"""Check a small, explicit subset of the CIS Kubernetes Benchmark on this cluster."""
import json
import os
import subprocess
import sys

CLUSTER = sys.argv[1] if len(sys.argv) > 1 else 'lab27'
NODE = f'{CLUSTER}-control-plane'
KUBECTL = ['kubectl', f'--kubeconfig={os.path.expanduser(f"~/labs/{CLUSTER}/kubeconfig")}',
           f'--context=kind-{CLUSTER}', '--request-timeout=10s']


def run(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'command failed')
    return result.stdout.strip()


def node_file(path):
    """Mode and ownership of a file on the control-plane node."""
    return run(['docker', 'exec', NODE, 'stat', '-c', '%a %U:%G', path])


def apiserver_flags():
    """The flags the running API server was started with, read from its mirror Pod."""
    out = run(KUBECTL + ['-n', 'kube-system', 'get', 'pod', f'kube-apiserver-{NODE}', '-o', 'json'])
    return json.loads(out)['spec']['containers'][0]['command']


def flag_value(flags, name):
    for flag in flags:
        if flag.startswith(f'--{name}='):
            return flag.split('=', 1)[1]
    return None


def kubelet_config():
    out = run(KUBECTL + ['get', '--raw', f'/api/v1/nodes/{NODE}/proxy/configz'])
    return json.loads(out)['kubeletconfig']


def cluster_admin_subjects():
    out = run(KUBECTL + ['get', 'clusterrolebindings', '-o', 'json'])
    subjects = []
    for binding in json.loads(out)['items']:
        if binding['roleRef']['name'] != 'cluster-admin':
            continue
        for subject in binding.get('subjects') or []:
            subjects.append(f"{subject['kind']}/{subject['name']}")
    return sorted(subjects)


DEFAULT_ADMINS = {'Group/system:masters', 'Group/kubeadm:cluster-admins'}


def controls():
    flags = apiserver_flags()
    kubelet = kubelet_config()
    subjects = cluster_admin_subjects()
    anonymous = kubelet.get('authentication', {}).get('anonymous', {}).get('enabled')
    extra = [s for s in subjects if s not in DEFAULT_ADMINS]
    manifest = node_file('/etc/kubernetes/manifests/kube-apiserver.yaml')
    admin = node_file('/etc/kubernetes/admin.conf')
    return [
        ('1.1.1', 'kube-apiserver manifest is 600 root:root', '600 root:root', manifest, manifest == '600 root:root'),
        ('1.1.13', 'admin.conf is 600 root:root', '600 root:root', admin, admin == '600 root:root'),
        ('1.2.1', 'API server --anonymous-auth=false', 'false',
         flag_value(flags, 'anonymous-auth') or 'unset (defaults to true)', flag_value(flags, 'anonymous-auth') == 'false'),
        ('1.2.21', 'API server --profiling=false', 'false',
         flag_value(flags, 'profiling') or 'unset (defaults to true)', flag_value(flags, 'profiling') == 'false'),
        ('4.2.1', 'kubelet anonymous authentication disabled', 'false', f'{anonymous}', anonymous is False),
        ('5.1.1', 'cluster-admin bound only to the default groups', 'no extra subjects',
         ', '.join(extra) if extra else 'none', not extra),
    ]


try:
    results = controls()
except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as error:
    print(f'scan failed: {type(error).__name__}: {error}')
    raise SystemExit(2)

for number, title, expected, observed, passed in results:
    print(f'{number:<7} {"PASS" if passed else "FAIL"}  {title}')
    print(f'{"":<7}       expected={expected} observed={observed}')
print(f'summary: {sum(1 for r in results if r[4])} pass, {sum(1 for r in results if not r[4])} fail, '
      f'{len(results)} controls checked')
