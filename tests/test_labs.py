"""Regression checks for the learning interface and changed measurement logic."""
import importlib.util
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lab_content import fixture_path, load_labs, render_card


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


startup = module('startup', fixture_path('12', 'startup-check.py'))
client = module('client', fixture_path('15', 'client.py'))


class Clock:
    now = 0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class StartupDeadlineTests(unittest.TestCase):
    def test_early_docker_failure_cannot_leave_a_previous_diagnostic_as_current(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / 'diagnostics').mkdir()
            stale = workspace / 'diagnostics/run-1.json'
            stale.write_text('previous run')
            with patch.object(startup, 'WORKSPACE', workspace), patch.object(startup.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'docker')):
                with self.assertRaises(subprocess.CalledProcessError):
                    startup.run(1)
            self.assertFalse(stale.exists())

    def test_diagnostics_discard_events_from_previous_pod_uid(self):
        responses = [
            {'metadata': {'uid': 'new-pod'}}, {}, {'items': []},
            {'items': [{'involvedObject': {'uid': uid}} for uid in ('old-pod', 'new-pod')]},
        ]
        with patch.object(startup, 'k', side_effect=[json.dumps(value) for value in responses]):
            result = startup.diagnostics({'success': 0})
        self.assertEqual(result['events']['items'], [{'involvedObject': {'uid': 'new-pod'}}])

    def test_diagnostic_errors_are_not_empty_successful_reads(self):
        with patch.object(startup, 'k', side_effect=subprocess.CalledProcessError(1, 'kubectl', stderr='API unavailable')):
            result = startup.diagnostics({'success': 0})
        for key in ('pod', 'service', 'endpointslices', 'events'):
            self.assertIn('diagnostic_error', result[key])
            self.assertEqual(result[key]['detail'], 'API unavailable')

    def test_completed_miss_saves_fresh_evidence_before_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / 'diagnostics').mkdir()
            (workspace / 'diagnostics/run-20.json').write_text('stale')
            inspect = subprocess.CompletedProcess([], 0, stdout='[{"NetworkSettings":{"Networks":{"kind":{"IPAddress":"127.0.0.1"}}}}]')
            order = []
            def capture(trial):
                order.append('capture')
                return {'trial': trial, 'pod': {'metadata': {'uid': 'fresh'}}}
            with patch.object(startup, 'WORKSPACE', workspace), patch.object(startup, 'cleanup', side_effect=lambda: order.append('cleanup')), patch.object(startup.subprocess, 'run', return_value=inspect), patch.object(startup, 'k', return_value='applied'), patch.object(startup, 'probe_until', return_value=(0, 30)), patch.object(startup, 'diagnostics', side_effect=capture), redirect_stdout(io.StringIO()):
                startup.run(1)
            self.assertEqual(order, ['cleanup', 'capture', 'cleanup'])
            self.assertFalse((workspace / 'diagnostics/run-20.json').exists())
            evidence = json.loads((workspace / 'diagnostics/run-1.json').read_text())
            self.assertEqual(evidence['trial']['success'], 0)
            self.assertEqual(evidence['trial']['elapsed_seconds'], 30)
            self.assertIn('ce_start_success 0', (workspace / 'metrics/start.prom').read_text())

    def test_response_after_deadline_is_not_success(self):
        clock = Clock()

        class Opener:
            def open(self, url, timeout):
                clock.sleep(31)
                return Response()

        ok, elapsed = startup.probe_until('unused', 0, 30, clock.time, clock.sleep, Opener())
        self.assertEqual(ok, 0)
        self.assertGreater(elapsed, 30)

    def test_connect_errors_are_sampled_until_budget(self):
        clock = Clock()

        class Opener:
            def open(self, url, timeout):
                clock.sleep(timeout)
                raise OSError('not ready')

        ok, elapsed = startup.probe_until('unused', 0, 30, clock.time, clock.sleep, Opener())
        self.assertEqual((ok, elapsed), (0, 30))

    def test_http_success_before_deadline(self):
        clock = Clock()

        class Opener:
            def open(self, url, timeout):
                clock.sleep(0.1)
                return Response()

        self.assertEqual(startup.probe_until('unused', 0, 30, clock.time, clock.sleep, Opener()), (1, 0.1))

    def test_submission_error_cleans_up_without_overwriting_previous_metric(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / 'metrics').mkdir()
            metric = workspace / 'metrics/start.prom'
            metric.write_text('previous completed trial')
            inspect = subprocess.CompletedProcess([], 0, stdout='[{"NetworkSettings":{"Networks":{"kind":{"IPAddress":"127.0.0.1"}}}}]')
            with patch.object(startup, 'WORKSPACE', workspace), patch.object(startup, 'cleanup') as cleanup, patch.object(startup.subprocess, 'run', return_value=inspect), patch.object(startup, 'k', side_effect=subprocess.CalledProcessError(1, 'kubectl')):
                with self.assertRaises(subprocess.CalledProcessError):
                    startup.run(1)
                self.assertEqual(cleanup.call_count, 2)
                self.assertEqual(metric.read_text(), 'previous completed trial')


class RetryAccountingTests(unittest.TestCase):
    def test_attempt_limits_and_early_success(self):
        for retries, failing, expected_attempts in ((0, True, 20), (1, True, 40), (1, False, 20)):
            with self.subTest(retries=retries, failing=failing), tempfile.TemporaryDirectory() as directory:
                workspace = Path(directory)
                for port in (9001, 9002):
                    (workspace / f'arrivals-{port}.log').touch()
                calls = []

                class Opener:
                    def open(self, request, timeout):
                        calls.append(request)
                        # A failed proxy attempt visits both upstreams; success stops at one.
                        for port in ((9001, 9002) if failing else (9001,)):
                            with (workspace / f'arrivals-{port}.log').open('a') as log:
                                log.write(f'{request.get_header("X-lab-request")} {503 if failing else 200}\n')
                        if failing:
                            raise client.urllib.error.HTTPError(request.full_url, 503, 'fault', {}, None)
                        return Response()

                with patch.object(client.urllib.request, 'build_opener', return_value=Opener()), redirect_stdout(io.StringIO()):
                    successes, arrivals = client.run('fault' if failing else 'baseline', retries, workspace)
                self.assertEqual(len(calls), expected_attempts)
                self.assertEqual(arrivals, expected_attempts * (2 if failing else 1))
                self.assertEqual(successes, 0 if failing else 20)


class CardTests(unittest.TestCase):
    def test_question_keeps_teaching_content_but_not_solution_only_fields(self):
        for number, original in load_labs().items():
            with self.subTest(lab=number):
                lab = copy.deepcopy(original)
                lab['solution'] = 'SOLUTION_ONLY_MARKER'
                lab['transfer_solution'] = 'TRANSFER_ONLY_MARKER'
                for index, step in enumerate(lab['commands']):
                    step['expect'] = f'OBSERVATION_ONLY_MARKER_{index}'
                question = render_card(number, lab, 'question')
                solution = render_card(number, lab, 'solution')
                for marker in ('SOLUTION_ONLY_MARKER', 'TRANSFER_ONLY_MARKER', 'OBSERVATION_ONLY_MARKER'):
                    self.assertNotIn(marker, question)
                    self.assertIn(marker, solution)
                normalized = ' '.join(question.split())
                for text in (lab['prerequisites'], lab['task']['predict'], lab['task']['answer_with'], lab['task']['transfer'],
                             *lab['task']['brief']['theory'], *lab['task']['brief']['in_this_lab'],
                             *(reading['meaning'] for reading in lab['task']['brief']['readings'])):
                    self.assertIn(' '.join(text.split()), normalized)

    def test_all_questions_teach_before_commands_and_hide_answers(self):
        for number, lab in load_labs().items():
            with self.subTest(lab=number):
                question = render_card(number, lab, 'question')
                self.assertLess(question.index('THEORY YOU NEED'), question.index('PROCEDURE'))
                self.assertLess(question.index('HOW TO READ THE EVIDENCE'), question.index('PREDICT'))
                self.assertIn('RECORD YOUR RESULTS', question)
                self.assertNotIn(' '.join(lab['transfer_solution'].split()), ' '.join(question.split()))
                for command in lab['commands']:
                    self.assertIn(command['run'].strip(), question)

    def test_question_does_not_invoke_vm_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            # Empty PATH proves the Python entry point does not launch external tools.
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/labs.py'), '01', 'question'], env={'PATH': directory}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('THEORY YOU NEED', result.stdout)


class KubernetesFixtureTests(unittest.TestCase):
    def test_each_lab_uses_only_its_own_numbered_workspace(self):
        for number, lab in load_labs().items():
            for group in ('setup', 'reset', 'verify', 'commands', 'fallback'):
                for step in lab.get(group, []):
                    source = step.get('command', step.get('run', ''))
                    referenced = set(re.findall(r'labs/lab(\d{2})(?:/|\b)', source))
                    self.assertLessEqual(referenced, {number}, f'{number}/{group}: foreign workspace')

    def test_resource_and_listener_variants_isolate_their_faults(self):
        def fixture(lab, name):
            return yaml.safe_load(fixture_path(str(lab), f'{name}.yaml').read_text())

        good = fixture(19, 'good')
        unscheduled = fixture(19, 'unscheduled')
        cpu = unscheduled['spec']['containers'][0]['resources']['requests']
        self.assertEqual(cpu['cpu'], '1000')
        cpu['cpu'] = good['spec']['containers'][0]['resources']['requests']['cpu']
        self.assertEqual(unscheduled, good)
        oom = fixture(19, 'oom')['spec']['containers'][0]
        self.assertEqual(oom['resources']['requests'], good['spec']['containers'][0]['resources']['requests'])
        self.assertEqual(oom['resources']['limits']['memory'], '32Mi')

        server, loopback = fixture(20, 'server'), fixture(20, 'loopback')
        self.assertEqual(loopback['spec']['containers'][0]['command'][-1], '127.0.0.1')
        loopback['spec']['containers'][0]['command'][-1] = '0.0.0.0'
        self.assertEqual(loopback, server)

    def test_rollout_app_returns_the_injected_value_with_a_newline(self):
        resources = list(yaml.safe_load_all(fixture_path('21', 'app.yaml').read_text()))
        deployment = next(item for item in resources if item['kind'] == 'Deployment')
        app = deployment['spec']['template']['spec']['containers'][0]['command'][-1]
        from unittest.mock import Mock
        server = Mock()
        with patch('http.server.HTTPServer', return_value=server), patch.dict(os.environ, MESSAGE='test-value'):
            namespace = {}
            exec(compile(app, 'lab21-app', 'exec'), namespace)
            handler = namespace['Handler'].__new__(namespace['Handler'])
            handler.send_response = Mock()
            handler.end_headers = Mock()
            handler.wfile = io.BytesIO()
            handler.do_GET()
        self.assertEqual(handler.wfile.getvalue(), b'test-value\n')
        handler.send_response.assert_called_once_with(200)

    def test_consumer_observation_propagates_lookup_and_http_failure(self):
        self.assertIsNotNone(shutil.which('jq'), 'Install jq to exercise the real JSON selection logic')
        source = load_labs()['21']['setup'][0]['command']
        helper = source.split("<<'SH'\n", 1)[1].split('\nSH', 1)[0]
        # Stub only the API; jq still checks the actual selection logic.
        pod_json = json.dumps({'items': [{'metadata': {'name': 'consumer'}}]})
        cases = [
            'k21() { return 1; };',
            "k21() { printf '%s' '{\"items\":[]}'; };",
            f"k21() {{ if [[ $2 == pods ]]; then printf '%s' '{pod_json}'; else return 1; fi; }};",
        ]
        for stub in cases:
            with self.subTest(stub=stub):
                result = subprocess.run(['bash', '-c', helper + '\n' + stub + '\nresponses'], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, '')

    def test_consumer_observation_excludes_terminating_pods(self):
        self.assertIsNotNone(shutil.which('jq'), 'Install jq to exercise the real JSON selection logic')
        source = load_labs()['21']['setup'][0]['command']
        helper = source.split("<<'SH'\n", 1)[1].split('\nSH', 1)[0]
        pod_json = json.dumps({'items': [{'metadata': {'name': 'current'}}, {'metadata': {'name': 'old', 'deletionTimestamp': '2026-09-18T00:00:00Z'}}]})
        stub = f"k21() {{ if [[ $2 == pods ]]; then printf '%s' '{pod_json}'; elif [[ $3 == *current* ]]; then echo version-one; else return 1; fi; }};"
        result = subprocess.run(['bash', '-c', helper + '\n' + stub + '\nresponses'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'current version-one\n')

    def test_ha_recovery_preserves_state_until_health_and_readback_succeed(self):
        command = load_labs()['14']['commands'][-1]['run']
        stubs = 'h() { echo UNEXPECTED_API_CALL; }; ec() { echo UNEXPECTED_ETCD_CALL; }; curl() { echo UNEXPECTED_HTTP_CALL >&2; };\n'
        for flags in ('unset healthy observed', 'healthy=0; observed=1', 'healthy=1; observed=0'):
            with self.subTest(flags=flags):
                result = subprocess.run(['bash', '-c', stubs + flags + '\n' + command], capture_output=True, text=True)
                self.assertIn('STOP:', result.stdout)
                self.assertNotIn('UNEXPECTED_', result.stdout + result.stderr)

    def test_observation_helpers_propagate_api_failure(self):
        source = load_labs()['11']['setup'][1]['command']
        helpers = source[source.index('pings() {'):source.rindex('sleep 10')]
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory)
            jq = binary / 'jq'
            jq.write_text('#!/bin/sh\ncat >/dev/null\nexit 0\n')
            jq.chmod(0o755)
            env = dict(os.environ, PATH=f'{binary}:{os.environ["PATH"]}')
            for function in ('pings', 'readiness'):
                with self.subTest(function=function):
                    result = subprocess.run(['bash', '-c', helpers + '\nk() { return 1; }; SLOW_IP=127.0.0.1; ' + function], env=env, capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)

    def test_startup_verify_does_not_treat_api_errors_as_deleted_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            binary = home / 'bin'
            binary.mkdir()
            stub = binary / 'kubectl'
            stub.write_text('#!/bin/sh\necho "API unavailable" >&2\nexit 1\n')
            stub.chmod(0o755)
            workspace = home / 'labs/lab12'
            workspace.mkdir(parents=True)
            for name in ('startup.yaml', 'run.sh'):
                (workspace / name).write_text('fixture')
            env = dict(os.environ, HOME=str(home), PATH=f'{binary}:{os.environ["PATH"]}')
            result = subprocess.run(['bash', '-euo', 'pipefail', '-c', load_labs()['12']['verify'][0]['command']], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('API unavailable', result.stderr)

    def test_static_probe_and_startup_faults_change_the_intended_stage(self):
        tcp = yaml.safe_load(fixture_path('11', 'slow.yaml').read_text())
        http = yaml.safe_load(fixture_path('11', 'slow-http.yaml').read_text())
        self.assertIn('tcpSocket', tcp['spec']['containers'][1]['readinessProbe'])
        self.assertEqual(http['spec']['containers'][1]['readinessProbe']['httpGet']['port'], 8080)
        self.assertEqual(http['spec']['containers'][1]['readinessProbe']['timeoutSeconds'], 1)
        self.assertEqual(http['spec']['containers'][1]['readinessProbe']['failureThreshold'], 2)
        http['spec']['containers'][1]['readinessProbe'] = tcp['spec']['containers'][1]['readinessProbe']
        self.assertEqual(http, tcp, 'Probe comparison must not change another variable')
        # The extra Pod must be discoverable without being adopted by the baseline ReplicaSet.
        manifest = (ROOT / 'ansible/files/kubernetes/goldpinger.yaml').read_text()
        resources = list(yaml.safe_load_all(manifest))
        deployment = next(r for r in resources if r['kind'] == 'Deployment')
        service = next(r for r in resources if r['kind'] == 'Service')
        labels = tcp['metadata']['labels']
        self.assertFalse(all(labels.get(k) == v for k, v in deployment['spec']['selector']['matchLabels'].items()))
        self.assertTrue(all(labels.get(k) == v for k, v in service['spec']['selector'].items()))
        manifests = {name: list(yaml.safe_load_all(fixture_path('12', f'startup-{name}.yaml').read_text()))
                     for name in ('good', 'delayed', 'unscheduled', 'selector')}
        self.assertIn('sleep 45', manifests['delayed'][0]['spec']['containers'][0]['command'][-1])
        selector = manifests['selector'][1]['spec']['selector']
        self.assertFalse(all(manifests['selector'][0]['metadata']['labels'].get(k) == v for k, v in selector.items()))
        self.assertEqual(manifests['selector'][0], manifests['good'][0])
        self.assertEqual(manifests['unscheduled'][1], manifests['good'][1])
        self.assertEqual(manifests['unscheduled'][0]['spec']['nodeSelector'], {'chaos-labs.invalid/placement': 'missing'})


if __name__ == '__main__':
    unittest.main()
