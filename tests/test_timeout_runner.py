"""Exercise the generated Lab 01 runner without systemd or firewall access."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lab_content import load_labs


FAKE_SUDO = '''#!/usr/bin/env python3
import json, os, pathlib, sys
root = pathlib.Path(os.environ['RUNNER_TEST_DIR'])
args = sys.argv[1:]
with (root / 'calls.jsonl').open('a') as log:
    log.write(json.dumps(args) + '\\n')
if args == ['-v']:
    raise SystemExit(0)
if not args or args[0] != 'iptables':
    raise SystemExit('Unexpected sudo command: ' + repr(args))
args = args[1:]
state_path = root / 'rules.json'
rules = json.loads(state_path.read_text())
if args[:3] == ['-I', 'OUTPUT', '1']:
    if os.environ.get('FAIL_INSERT') == '1':
        raise SystemExit(43)
    rules.insert(0, args[3:])
elif args[:2] == ['-D', 'OUTPUT']:
    if args[2:] not in rules:
        raise SystemExit(1)
    rules.remove(args[2:])
elif args == ['-nvL', 'OUTPUT', '--line-numbers']:
    print('num pkts bytes target')
    for number, rule in enumerate(rules, 1):
        print(number, 1, 60, ' '.join(rule))
else:
    raise SystemExit('Unexpected iptables command: ' + repr(args))
state_path.write_text(json.dumps(rules))
'''

FAKE_CLIENT = '''import json, os, pathlib, sys
path = pathlib.Path(os.environ['RUNNER_TEST_DIR']) / 'clients.jsonl'
with path.open('a') as log:
    log.write(json.dumps({'TIMEOUT': os.environ.get('TIMEOUT')}) + '\\n')
print('harmless fake client')
sys.exit(int(os.environ.get('CLIENT_EXIT', '0')))
'''


class TimeoutRunnerTests(unittest.TestCase):
    foreign_rule = ['-p', 'tcp', '--dport', '9999', '-m', 'comment', '--comment', 'another-lab', '-j', 'DROP']
    lab_rule = ['-p', 'tcp', '-d', '127.0.0.1', '--dport', '6381', '-m', 'comment', '--comment', 'ce-lab01']

    def run_case(self, case, **overrides):
        setup = next(step['command'] for step in load_labs()['01']['setup'] if "cat > run.sh <<'SH'" in step['command'])
        runner = setup.split("cat > run.sh <<'SH'\n", 1)[1].split('\nSH', 1)[0]
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            binary = workspace / 'bin'
            binary.mkdir()
            sudo = binary / 'sudo'
            sudo.write_text(FAKE_SUDO)
            sudo.chmod(0o755)
            (workspace / 'run.sh').write_text(runner)
            (workspace / 'client.py').write_text(FAKE_CLIENT)
            (workspace / 'rules.json').write_text(json.dumps([self.foreign_rule]))
            env = dict(os.environ, RUNNER_TEST_DIR=directory, TIMEOUT='3.75', PATH=f'{binary}{os.pathsep}{os.environ["PATH"]}')
            env.update(overrides)
            result = subprocess.run(['bash', 'run.sh', case], cwd=workspace, env=env, capture_output=True, text=True, timeout=10)

            def records(name):
                path = workspace / name
                return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

            return result, json.loads((workspace / 'rules.json').read_text()), records('calls.jsonl'), records('clients.jsonl')

    def assert_cleanup_is_scoped(self, rules, calls):
        self.assertEqual(rules, [self.foreign_rule], 'The injected rule must be removed and the foreign rule retained')
        deletions = [call[3:] for call in calls if call[:3] == ['iptables', '-D', 'OUTPUT']]
        self.assertTrue(deletions)
        for rule in deletions:
            self.assertIn(rule, [self.lab_rule + ['-j', 'DROP'], self.lab_rule + ['-j', 'REJECT', '--reject-with', 'tcp-reset']])

    def test_only_requested_case_runs_with_explicit_timeout_environment(self):
        for case, target, expected_timeout in (
            ('reject', ['REJECT', '--reject-with', 'tcp-reset'], None),
            ('drop', ['DROP'], None),
            ('drop-timeout', ['DROP'], '0.5'),
        ):
            with self.subTest(case=case):
                result, rules, calls, clients = self.run_case(case)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(clients, [{'TIMEOUT': expected_timeout}])
                insertions = [call[4:] for call in calls if call[:4] == ['iptables', '-I', 'OUTPUT', '1']]
                self.assertEqual(insertions, [self.lab_rule + ['-j'] + target])
                self.assertIn('client exit=0', result.stdout)
                self.assert_cleanup_is_scoped(rules, calls)

    def test_invalid_case_cannot_touch_firewall_or_run_client(self):
        result, rules, calls, clients = self.run_case('invalid')
        self.assertEqual(result.returncode, 2)
        self.assertIn('Usage:', result.stderr)
        self.assertEqual((calls, clients), ([], []))
        self.assertEqual(rules, [self.foreign_rule])

    def test_client_failure_is_reported_and_rule_is_removed(self):
        result, rules, calls, clients = self.run_case('drop', CLIENT_EXIT='23')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('client exit=23', result.stdout)
        self.assertEqual(len(clients), 1)
        self.assert_cleanup_is_scoped(rules, calls)

    def test_failed_rule_installation_stops_before_client_and_cleans_up(self):
        result, rules, calls, clients = self.run_case('reject', FAIL_INSERT='1')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(clients, [])
        self.assert_cleanup_is_scoped(rules, calls)


if __name__ == '__main__':
    unittest.main()
