"""Read exact etcd value bytes independently of the Kubernetes API."""
import argparse
import base64
import json
from pathlib import Path
import re
import subprocess

NODE = 'lab36-control-plane'
MARKER = b'ce-lab36-demo'


def read_record(name):
    if name not in ('legacy', 'fresh'):
        raise ValueError('Only this lab\'s two Secret names are allowed')
    result = subprocess.run(['docker', 'exec', NODE, 'crictl', 'ps', '--name', 'etcd', '-q'],
                            check=True, capture_output=True, text=True)
    containers = result.stdout.split()
    if len(containers) != 1:
        raise ValueError('Expected exactly one running etcd container')
    result = subprocess.run(['docker', 'exec', NODE, 'crictl', 'exec', containers[0], 'etcdctl',
        '--endpoints=https://127.0.0.1:2379', '--cacert=/etc/kubernetes/pki/etcd/ca.crt',
        '--cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt',
        '--key=/etc/kubernetes/pki/etcd/healthcheck-client.key',
        'get', f'/registry/secrets/ce-lab36/{name}', '--write-out=json'],
        check=True, capture_output=True, text=True)
    values = json.loads(result.stdout).get('kvs', [])
    if len(values) != 1:
        raise ValueError('The requested etcd record was not found; no storage conclusion is possible')
    return base64.b64decode(values[0]['value'], validate=True)


def describe(raw):
    if raw.startswith(b'k8s:enc:'):
        prefix = b':'.join(raw.split(b':', 5)[:5]) + b':'
        label = prefix.decode('ascii')
    else:
        label = 'no Kubernetes encryption prefix'
    return f'bytes={len(raw)}; prefix={label}; demo_password_visible={MARKER in raw}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', choices=['legacy', 'fresh'])
    parser.add_argument('phase')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]+', args.phase):
        parser.error('phase must be a simple lowercase label')
    raw = read_record(args.name)
    target = Path.home() / 'labs/lab36' / f'{args.phase}-{args.name}.bin'
    target.write_bytes(raw)
    target.chmod(0o600)
    print(f'{args.name}: {describe(raw)}; saved={target.name}')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(f'STOP: etcd observation failed: {error.stderr.strip()}')
    except (ValueError, OSError) as error:
        raise SystemExit(f'STOP: {error}')
