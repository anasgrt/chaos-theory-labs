"""Exercise platform TLS and real Ansible templates without starting a VM."""
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class PlatformTLSTests(unittest.TestCase):
    def run_helper(self, directory, hostname='rancher.chaos.test'):
        return subprocess.run(['bash', str(ROOT / 'ansible/files/platform-tls.sh'),
                               str(directory), hostname], capture_output=True, text=True, timeout=60)

    def test_reprovision_preserves_ca_and_valid_certificate_and_renews_wrong_hostname(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first = self.run_helper(directory)
            self.assertEqual(first.returncode, 0, first.stderr)
            original = {name: (directory / name).read_bytes() for name in ('ca.crt', 'ca.key', 'tls.crt', 'tls.key')}
            second = self.run_helper(directory)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertNotIn('changed:', second.stdout)
            for name, data in original.items():
                self.assertEqual((directory / name).read_bytes(), data)
            for name in ('ca.key', 'tls.key'):
                self.assertEqual((directory / name).stat().st_mode & 0o777, 0o600)
            renewed = self.run_helper(directory, 'new.chaos.test')
            self.assertEqual(renewed.returncode, 0, renewed.stderr)
            self.assertEqual((directory / 'ca.crt').read_bytes(), original['ca.crt'])
            self.assertEqual((directory / 'ca.key').read_bytes(), original['ca.key'])
            self.assertNotEqual((directory / 'tls.crt').read_bytes(), original['tls.crt'])
            verify = subprocess.run(['openssl', 'verify', '-CAfile', str(directory / 'ca.crt'),
                                     '-verify_hostname', 'new.chaos.test', str(directory / 'tls.crt')], capture_output=True)
            self.assertEqual(verify.returncode, 0, verify.stderr)

    def test_incomplete_ca_fails_without_replacing_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / 'ca.key').write_text('existing key must not be replaced')
            result = self.run_helper(directory)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((directory / 'ca.key').read_text(), 'existing key must not be replaced')
            self.assertFalse((directory / 'ca.crt').exists())

    def test_hostname_cannot_inject_shell_or_openssl_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            for hostname in ('$(touch injected)', 'example.test\nDNS:other.test', '-bad'):
                result = self.run_helper(Path(tmp), hostname)
                self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(Path(tmp).iterdir()), [])


class PlatformConfigurationTests(unittest.TestCase):
    def test_health_checks_fail_on_unready_node_tls_error_or_wrong_response(self):
        # Execute the real task conditions; replace only external commands so no
        # service or cluster is contacted, and shorten production retry budgets.
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            stub = directory / 'command.py'
            stub.write_text('''import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ['PLATFORM_CALLS'], 'a') as log:
    log.write(json.dumps(args) + '\\n')
scenario = os.environ['PLATFORM_SCENARIO']
command = Path(args[0]).name
if command == 'systemctl':
    assert args[1:] == ['is-active', 'rke2-server']
    print('active')
elif command == 'kubectl':
    assert '--kubeconfig=/etc/rancher/rke2/rke2.yaml' in args
    assert '--context=default' in args
    if '--raw=/readyz' in args:
        print('ok')
    elif 'wait' in args:
        assert '--for=condition=Ready' in args and 'node/chaos-labs' in args
        sys.exit(1 if scenario == 'unready-node' else 0)
    else:
        assert 'rollout' in args and 'deployment/rancher' in args
elif command == 'curl':
    assert '--cacert' in args and '--resolve' in args
    assert '-k' not in args and '--insecure' not in args
    if scenario == 'tls-error':
        sys.exit(60)
    print('wrong response' if scenario == 'wrong-response' else 'pong')
elif command == 'rke2-kubectl':
    assert args[1:] == ['get', 'nodes', '--request-timeout=15s']
else:
    raise AssertionError(args)
''')
            tasks = yaml.safe_load((ROOT / 'ansible/tasks/platform-verify.yml').read_text())
            for task in tasks:
                command = task.get('ansible.builtin.command')
                if command:
                    argv = command['argv'] if isinstance(command, dict) else shlex.split(command)
                    task['ansible.builtin.command'] = {'argv': ['python3', str(stub), *argv]}
                if 'retries' in task:
                    task.update(retries=1, delay=0)
            playbook = directory / 'health.yml'
            playbook.write_text(yaml.safe_dump([{
                'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars': {'lab_user': 'unused', 'lab_home': tmp,
                         'rancher_hostname': 'rancher.chaos.test', 'platform_ip': '192.168.56.10'},
                'tasks': tasks,
            }]))
            for scenario in ('healthy', 'unready-node', 'tls-error', 'wrong-response'):
                with self.subTest(scenario=scenario):
                    calls = directory / (scenario + '.jsonl')
                    result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(playbook)],
                        env=dict(os.environ, ANSIBLE_CONFIG=str(ROOT / 'ansible/ansible.cfg'),
                                 PLATFORM_CALLS=str(calls), PLATFORM_SCENARIO=scenario),
                        capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode == 0, scenario == 'healthy', result.stdout + result.stderr)
                    executed = [json.loads(line) for line in calls.read_text().splitlines()]
                    if scenario == 'unready-node':
                        self.assertFalse(any(Path(args[0]).name == 'curl' for args in executed))

    def test_management_wrapper_rejects_target_overrides_before_invoking_kubectl(self):
        for flag in ('--kubeconfig=/tmp/foreign', '--context=kind-lab03', '--server=x', '-s', '-shttps://foreign', '--insecure-skip-tls-verify'):
            result = subprocess.run(['bash', str(ROOT / 'ansible/files/rke2-kubectl'), 'get', 'nodes', flag], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('only the management', result.stderr)

    def test_real_ansible_templates_keep_tls_and_kubeconfig_references_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,',
                                     str(ROOT / 'tests/ansible/platform.yml'),
                                     '-e', json.dumps({'platform_test_output': tmp})],
                                    env=dict(os.environ, ANSIBLE_CONFIG=str(ROOT / 'ansible/ansible.cfg')),
                                    capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            directory = Path(tmp)
            config = yaml.safe_load((directory / 'rke2-config.yaml').read_text())
            self.assertEqual(config['ingress-controller'], 'traefik')
            self.assertEqual(config['write-kubeconfig-mode'], '0600')
            self.assertNotEqual(config['cluster-cidr'], '10.244.0.0/16')
            values = yaml.safe_load((directory / 'rancher-values.yaml').read_text())
            self.assertTrue(values['privateCA'])
            self.assertEqual(values['agentTLSMode'], 'strict')
            self.assertEqual(values['ingress']['tls']['source'], 'secret')
            self.assertEqual(values['replicas'], 1)
            dns = yaml.safe_load((directory / 'rke2-coredns-config.yaml').read_text())
            plugins = yaml.safe_load(dns['spec']['valuesContent'])['servers'][0]['plugins']
            hosts = next(p['configBlock'] for p in plugins if p['name'] == 'hosts')
            self.assertIn(config['node-ip'] + ' ' + values['hostname'], hosts)
            kubeconfig = yaml.safe_load((directory / 'rke2-kubeconfig.yaml').read_text())
            context = kubeconfig['contexts'][0]
            self.assertEqual(kubeconfig['current-context'], context['name'])
            self.assertEqual(context['name'], 'rke2-management')
            self.assertIn(context['context']['cluster'], {c['name'] for c in kubeconfig['clusters']})
            self.assertIn(context['context']['user'], {u['name'] for u in kubeconfig['users']})
            self.assertEqual((directory / 'rke2-kubeconfig.yaml').stat().st_mode & 0o777, 0o600)

    def test_platform_shell_blocks_parse(self):
        for name in ('platform-install.yml', 'rancher.yml'):
            for task in yaml.safe_load((ROOT / 'ansible/tasks' / name).read_text()):
                source = task.get('ansible.builtin.shell')
                if source:
                    # Replace the two quoted template values only; Ansible rendering is tested above.
                    source = re.sub(r'{{[^}]+}}', 'example.test', source)
                    result = subprocess.run(['bash', '-n'], input=source, text=True, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
