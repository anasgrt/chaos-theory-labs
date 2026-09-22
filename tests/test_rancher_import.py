"""Run the real import and removal tasks against a stub Rancher API.

No VM, kind cluster or Rancher server is started. A local HTTP server answers
the Rancher endpoints the tasks call, so the conditions, ordering, retries and
failure handling that ship in ansible/tasks are the ones exercised here.
"""
import contextlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOKEN = 'token-abc:secret'


class RancherStub(ThreadingHTTPServer):
    """Minimal stand-in for the Rancher v3 API used by the lab tasks."""

    allow_reuse_address = True

    def __init__(self, scenario):
        super().__init__(('127.0.0.1', 0), _Handler)
        self.scenario = scenario
        self.calls = []
        self.clusters = {}
        self.server_url = '' if scenario == 'no-server-url' else 'https://rancher.chaos.test'
        self.next_id = 0
        if scenario in ('remove', 'remove-stuck'):
            self.clusters['c-lab03'] = {'id': 'c-lab03', 'name': 'lab03', 'state': 'active'}
            self.clusters['c-lab09'] = {'id': 'c-lab09', 'name': 'lab09', 'state': 'active'}

    @property
    def url(self):
        return 'http://127.0.0.1:%d' % self.server_address[1]


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        return self.headers.get('Authorization') == 'Bearer ' + TOKEN

    def do_GET(self):
        parsed = urlparse(self.path)
        self.server.calls.append(('GET', parsed.path))
        if parsed.path.startswith('/v3/import/'):
            # Rancher serves the registration manifest by token in the path.
            body = b'apiVersion: v1\nkind: Namespace\nmetadata:\n  name: cattle-system\n'
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        if not self._authorized():
            return self._send(401, {'type': 'error'})
        if parsed.path == '/v3/settings/server-url':
            return self._send(200, {'value': self.server.server_url})
        if parsed.path == '/v3/clusters':
            name = parse_qs(parsed.query).get('name', [''])[0]
            data = [c for c in self.server.clusters.values() if c['name'] == name]
            return self._send(200, {'data': data})
        if parsed.path.startswith('/v3/clusters/'):
            cluster = self.server.clusters.get(parsed.path.rsplit('/', 1)[1])
            return self._send(200, cluster) if cluster else self._send(404, {'type': 'error'})
        if parsed.path == '/v3/clusterregistrationtokens':
            cluster_id = parse_qs(parsed.query).get('clusterId', [''])[0]
            url = '%s/v3/import/%s_%s.yaml' % (self.server.url, TOKEN, cluster_id)
            return self._send(200, {'data': [{'manifestUrl': url}]})
        self._send(404, {'type': 'error'})

    def do_POST(self):
        parsed = urlparse(self.path)
        self.server.calls.append(('POST', parsed.path))
        length = int(self.headers.get('Content-Length') or 0)
        body = json.loads(self.rfile.read(length) or b'{}')
        if parsed.path == '/v3-public/localProviders/local':
            if self.server.scenario == 'rancher-down' or body.get('password') != 'SuperAdmin@123':
                return self._send(401, {'type': 'error'})
            return self._send(201, {'token': TOKEN})
        if not self._authorized():
            return self._send(401, {'type': 'error'})
        if parsed.path == '/v3/tokens':
            return self._send(200, {})
        if parsed.path == '/v3/clusters':
            self.server.next_id += 1
            cluster = {'id': 'c-new%d' % self.server.next_id, 'name': body['name'], 'state': 'active'}
            self.server.clusters[cluster['id']] = cluster
            return self._send(201, cluster)
        self._send(404, {'type': 'error'})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        self.server.calls.append(('DELETE', parsed.path))
        if not self._authorized():
            return self._send(401, {'type': 'error'})
        cluster_id = parsed.path.rsplit('/', 1)[1]
        if cluster_id not in self.server.clusters:
            return self._send(404, {'type': 'error'})
        if self.server.scenario != 'remove-stuck':
            del self.server.clusters[cluster_id]
        return self._send(200, {'id': cluster_id})


@contextlib.contextmanager
def stub_server(scenario):
    """Run the stub Rancher API for the duration of a test."""
    stub = RancherStub(scenario)
    thread = threading.Thread(target=stub.serve_forever, daemon=True)
    thread.start()
    try:
        yield stub
    finally:
        stub.shutdown()
        stub.server_close()
        thread.join(timeout=10)


def run_tasks(tasks_file, stub, extra_vars, tmp, run='1', expect_success=True):
    """Execute a shipped task file against a running stub.

    Returns the process result, the kubectl invocations made by this run only,
    and the combined output.
    """
    directory = Path(tmp)
    kubectl_log = directory / ('kubectl-%s.jsonl' % run)
    binary = directory / 'bin'
    binary.mkdir(exist_ok=True)
    (binary / 'kubectl').write_text(
        '#!/usr/bin/env python3\n'
        'import json, os, sys\n'
        'with open(os.environ["KUBECTL_LOG"], "a") as log:\n'
        '    log.write(json.dumps({"argv": sys.argv[1:], "stdin": sys.stdin.read()}) + "\\n")\n'
    )
    (binary / 'kubectl').chmod(0o755)

    tasks = yaml.safe_load((ROOT / 'ansible/tasks' / tasks_file).read_text())
    # Point the shipped tasks at the stub; shorten only the production waits.
    tasks = json.loads(json.dumps(tasks).replace('https://{{ rancher_hostname }}', stub.url))

    def shorten(node):
        if isinstance(node, dict):
            if 'retries' in node:
                node['retries'] = 3
                node['delay'] = 0
            if 'ansible.builtin.uri' in node:
                node['ansible.builtin.uri'].pop('ca_path', None)
            for value in node.values():
                shorten(value)
        elif isinstance(node, list):
            for value in node:
                shorten(value)

    shorten(tasks)
    playbook = directory / ('play-%s.yml' % run)
    variables = {
        'rancher_hostname': 'rancher.chaos.test',
        'rancher_admin_password': 'SuperAdmin@123',
        'lab_rancher_ca': str(directory / 'ca.crt'),
        'lab_workspace': str(directory / 'lab'),
    }
    variables.update(extra_vars)
    playbook.write_text(yaml.safe_dump([{
        'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
        'environment': {'PATH': '%s:%s' % (binary, os.environ['PATH']),
                        'KUBECTL_LOG': str(kubectl_log)},
        'vars': variables, 'tasks': tasks,
    }]))
    result = subprocess.run(
        ['ansible-playbook', '-i', 'localhost,', str(playbook)],
        env=dict(os.environ, ANSIBLE_CONFIG=str(ROOT / 'ansible/ansible.cfg')),
        capture_output=True, text=True, timeout=300)
    output = result.stdout + result.stderr
    if expect_success:
        assert result.returncode == 0, output
    applied = [json.loads(line) for line in kubectl_log.read_text().splitlines()] \
        if kubectl_log.exists() else []
    return result, applied, output


@unittest.skipUnless(shutil.which('ansible-playbook'), 'Ansible is required')
class ImportTests(unittest.TestCase):
    def test_import_creates_one_cluster_applies_the_agent_and_is_idempotent(self):
        variables = {'lab_id': '03', 'lab_cluster': 'lab03'}
        with stub_server('import') as stub, tempfile.TemporaryDirectory(prefix='chaos-import-') as tmp:
            _, applied, _ = run_tasks('rancher-import.yml', stub, variables, tmp, run='first')

            self.assertEqual([c['name'] for c in stub.clusters.values()], ['lab03'])
            self.assertEqual(len(applied), 1)
            self.assertIn('cattle-system', applied[0]['stdin'])
            # The agent must land in this lab's cluster only, never the management one.
            self.assertIn('--context=kind-lab03', applied[0]['argv'])
            self.assertIn('--kubeconfig=' + tmp + '/lab/kubeconfig', applied[0]['argv'])
            self.assertEqual(applied[0]['argv'][-3:], ['apply', '-f', '-'])
            creates = [c for c in stub.calls if c == ('POST', '/v3/clusters')]
            self.assertEqual(len(creates), 1)
            # Every login is handed back, so no long-lived token is left behind.
            self.assertEqual(sum(1 for _, p in stub.calls if p == '/v3/tokens'),
                             sum(1 for _, p in stub.calls if p == '/v3-public/localProviders/local'))

            # Setting the same lab up again must reuse the record, not add a second.
            _, applied_again, _ = run_tasks('rancher-import.yml', stub, variables, tmp, run='second')
            self.assertEqual([c['name'] for c in stub.clusters.values()], ['lab03'])
            self.assertEqual(len(applied_again), 1)
            self.assertEqual(len([c for c in stub.calls if c == ('POST', '/v3/clusters')]), 1,
                             'a second setup must not create a second Rancher cluster')

    def test_import_names_the_cluster_after_its_own_lab(self):
        with stub_server('import') as stub, tempfile.TemporaryDirectory(prefix='chaos-name-') as tmp:
            run_tasks('rancher-import.yml', stub, {'lab_id': '21', 'lab_cluster': 'lab21'}, tmp)
            self.assertEqual({c['name'] for c in stub.clusters.values()}, {'lab21'})

    def test_import_fails_with_guidance_when_the_server_url_is_unpublished(self):
        with stub_server('no-server-url') as stub, \
                tempfile.TemporaryDirectory(prefix='chaos-url-') as tmp:
            result, applied, output = run_tasks(
                'rancher-import.yml', stub, {'lab_id': '03', 'lab_cluster': 'lab03'}, tmp,
                expect_success=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('server-url', output)
            self.assertIn('./lab.sh provision', output)
            self.assertEqual(applied, [], 'no agent may be installed without a server URL')
            self.assertEqual(stub.clusters, {}, 'no cluster record may be left behind')


@unittest.skipUnless(shutil.which('ansible-playbook'), 'Ansible is required')
class UnimportTests(unittest.TestCase):
    def test_removal_deletes_only_this_lab_and_waits_for_rancher(self):
        with stub_server('remove') as stub, tempfile.TemporaryDirectory(prefix='chaos-rm-') as tmp:
            _, applied, _ = run_tasks('rancher-unimport.yml', stub,
                                      {'lab_id': '03', 'lab_cluster': 'lab03'}, tmp)
            self.assertEqual({c['name'] for c in stub.clusters.values()}, {'lab09'})
            self.assertIn(('DELETE', '/v3/clusters/c-lab03'), stub.calls)
            self.assertNotIn(('DELETE', '/v3/clusters/c-lab09'), stub.calls)
            self.assertEqual(applied, [], 'removal must not touch any cluster API')

    def test_removal_succeeds_and_warns_when_rancher_is_unreachable(self):
        with stub_server('rancher-down') as stub, \
                tempfile.TemporaryDirectory(prefix='chaos-down-') as tmp:
            result, _, output = run_tasks('rancher-unimport.yml', stub,
                                          {'lab_id': '03', 'lab_cluster': 'lab03'}, tmp)
            self.assertEqual(result.returncode, 0, 'reset must never be blocked by Rancher')
            self.assertIn('Rancher was unreachable', output)

    def test_removal_reports_a_cluster_that_rancher_keeps_listing(self):
        with stub_server('remove-stuck') as stub, \
                tempfile.TemporaryDirectory(prefix='chaos-stuck-') as tmp:
            result, _, output = run_tasks('rancher-unimport.yml', stub,
                                          {'lab_id': '03', 'lab_cluster': 'lab03'}, tmp)
            self.assertEqual(result.returncode, 0)
            self.assertIn('Rancher still lists the cluster lab03', output)

    def test_removal_is_quiet_when_the_lab_was_never_imported(self):
        with stub_server('remove') as stub, tempfile.TemporaryDirectory(prefix='chaos-none-') as tmp:
            result, _, output = run_tasks('rancher-unimport.yml', stub,
                                          {'lab_id': '11', 'lab_cluster': 'lab11'}, tmp)
            self.assertEqual(result.returncode, 0)
            self.assertEqual({c['name'] for c in stub.clusters.values()}, {'lab03', 'lab09'})
            self.assertFalse(any(method == 'DELETE' for method, _ in stub.calls))
            self.assertNotIn('Rancher still lists', output)


class WiringTests(unittest.TestCase):
    """The lifecycle must import after the cluster exists and remove before it goes."""

    def test_setup_imports_after_the_cluster_and_reset_removes_before_deletion(self):
        tasks = yaml.safe_load((ROOT / 'ansible/labs.yml').read_text())[0]['tasks']
        names = [t.get('ansible.builtin.include_tasks') for t in tasks]
        self.assertLess(names.index('tasks/kubernetes.yml'), names.index('tasks/rancher-import.yml'))

        reset = yaml.safe_load((ROOT / 'ansible/tasks/reset.yml').read_text())
        titles = [t['name'] for t in reset]
        unimport = next(i for i, t in enumerate(reset)
                        if t.get('ansible.builtin.include_tasks') == 'rancher-unimport.yml')
        deletion = next(i for i, t in enumerate(titles) if t.startswith("Delete only this lab's kind cluster"))
        self.assertLess(unimport, deletion, 'Rancher must be able to reach the agent while removing')

    def test_both_sides_honour_the_configuration_toggle(self):
        setup = next(t for t in yaml.safe_load((ROOT / 'ansible/labs.yml').read_text())[0]['tasks']
                     if t.get('ansible.builtin.include_tasks') == 'tasks/rancher-import.yml')
        reset = next(t for t in yaml.safe_load((ROOT / 'ansible/tasks/reset.yml').read_text())
                     if t.get('ansible.builtin.include_tasks') == 'rancher-unimport.yml')
        for task in (setup, reset):
            self.assertIn('rancher_import_labs | default(true)', task['when'])
            self.assertIn('selected_lab.kubernetes | default(false)', task['when'])
        config = yaml.safe_load((ROOT / 'config/platform.yml').read_text())
        self.assertTrue(config['rancher_import_labs'])

    def test_provisioning_publishes_the_server_url(self):
        rancher = yaml.safe_load((ROOT / 'ansible/tasks/rancher.yml').read_text())
        patch = next(t for t in rancher if t['name'].startswith('Publish the Rancher server URL'))
        argv = patch['ansible.builtin.command']['argv']
        self.assertIn('settings.management.cattle.io', argv)
        self.assertIn('{"value": "https://{{ rancher_hostname }}"}', argv)
        self.assertEqual(patch['when'], "rancher_server_url.stdout != 'https://' + rancher_hostname")

    def test_the_agent_image_is_not_preloaded_into_lab_clusters(self):
        # Copying the 1.5 GiB agent into every kind node is slower than one
        # registry pull and exceeded the loader's per-image timeout in practice.
        provision = yaml.safe_load((ROOT / 'ansible/provision.yml').read_text())[0]
        self.assertFalse([i for i in provision['vars']['lab_images'] if 'rancher-agent' in i])
        loader = (ROOT / 'ansible/tasks/kubernetes.yml').read_text()
        self.assertNotIn('rancher-agent', loader)


if __name__ == '__main__':
    unittest.main()
