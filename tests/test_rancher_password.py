"""Run the real reset and login tasks against fake Kubernetes and local HTTP APIs."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class PasswordTests(unittest.TestCase):
    def test_reset_existing_password_verify_login_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            state = directory / 'password'
            calls = []
            scenario = 'healthy'

            class API(BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass

                def do_POST(self):
                    if self.path == '/v3/tokens?action=logout':
                        calls.append(('logout', self.path, self.headers.get('Authorization')))
                        self.send_response(200)
                        self.end_headers()
                        return
                    body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    calls.append(('login', body['username'], body['password']))
                    valid = (scenario != 'login-failure' and body['username'] == 'admin'
                             and body['password'] == state.read_text())
                    self.send_response(201 if valid else 401)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'id': 'token-check', 'token': 'token-check:secret'} if valid else {}).encode())

            server = ThreadingHTTPServer(('127.0.0.1', 0), API)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            stub = directory / 'kubectl.py'
            stub.write_text('''import json, os, sys
from pathlib import Path
args = sys.argv[1:]
assert '--kubeconfig=/etc/rancher/rke2/rke2.yaml' in args and '--context=default' in args
if 'get' in args:
    print(json.dumps({'items': [{'metadata': {'name': 'user-existing'}, 'username': 'admin'}]}))
elif 'create' in args:
    request = json.load(sys.stdin)
    assert request['kind'] == 'PasswordChangeRequest'
    assert request['spec']['userID'] == 'user-existing'
    if os.environ['SCENARIO'] == 'reset-failure':
        sys.exit(1)
    Path(os.environ['STATE']).write_text(request['spec']['newPassword'])
    print(json.dumps({'status': {'summary': 'Failed' if os.environ['SCENARIO'] == 'incomplete' else 'Completed'}}))
else:
    assert 'rollout' in args
''')
            tasks = yaml.safe_load((ROOT / 'ansible/tasks/rancher-password.yml').read_text())
            for task in tasks:
                if 'ansible.builtin.command' in task:
                    command = task['ansible.builtin.command']
                    command['argv'] = ['python3', str(stub), *command['argv'][1:]]
                if 'ansible.builtin.uri' in task:
                    uri = task['ansible.builtin.uri']
                    uri['url'] = uri['url'].replace('https://{{ rancher_hostname }}', f'http://127.0.0.1:{server.server_port}')
                    uri.pop('ca_path')
                if 'retries' in task:
                    task.update(retries=1, delay=0)
            # Include the real provisioning summary, so failures must prevent it.
            provision = yaml.safe_load((ROOT / 'ansible/provision.yml').read_text())
            tasks.append(provision[0]['tasks'][-1])
            playbook = directory / 'test.yml'
            playbook.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local',
                'gather_facts': False, 'vars': {'rancher_hostname': 'rancher.chaos.test',
                'rancher_admin_password': 'SuperAdmin@123'}, 'tasks': tasks}]))
            for scenario in ('healthy', 'healthy-again', 'reset-failure', 'incomplete', 'login-failure'):
                with self.subTest(scenario=scenario):
                    # Simulate a password changed in the UI before each provision.
                    state.write_text('DifferentPasswordFromUI')
                    calls.clear()
                    result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(playbook)],
                        env=dict(os.environ, ANSIBLE_CONFIG=str(ROOT / 'ansible/ansible.cfg'),
                                 SCENARIO=scenario, STATE=str(state)),
                        text=True, capture_output=True, timeout=60)
                    healthy = scenario.startswith('healthy')
                    self.assertEqual(result.returncode == 0, healthy, result.stdout + result.stderr)
                    self.assertEqual('Password: SuperAdmin@123' in result.stdout, healthy)
                    if healthy:
                        self.assertEqual(state.read_text(), 'SuperAdmin@123')
                        self.assertEqual(calls, [('login', 'admin', 'SuperAdmin@123'),
                                                ('logout', '/v3/tokens?action=logout', 'Bearer token-check:secret')])
                    elif scenario in ('reset-failure', 'incomplete'):
                        self.assertEqual(calls, [])
