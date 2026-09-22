"""Check that the simpler learner commands preserve trustworthy measurements."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lab_content import fixture_path, load_labs


def exercise(number, command, stubs='', home=None):
    env = dict(os.environ)
    if home is not None:
        env['HOME'] = str(home)
    # Run actual helper code and real jq, replacing only external observations/time.
    source = fixture_path(f'{number:02}', 'exercise.sh').read_text()
    return subprocess.run(['bash', '-c', source + '\nsleep() { :; };\n' + stubs + '\n' + command],
                          env=env, capture_output=True, text=True, timeout=15)


class ObservationTests(unittest.TestCase):
    def test_missing_api_data_is_not_an_empty_backend_set(self):
        for lab in (24, 25):
            for command in ('wait_backend_removed', 'wait_backend_ready'):
                with self.subTest(lab=lab, command=command):
                    result = exercise(lab, command, 'ksys() { return 1; };')
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('STOP:', result.stderr)

    def test_backend_wait_distinguishes_empty_unready_and_ready(self):
        for lab in (24, 25):
            for endpoints, removed, ready in (([], True, False),
                                              ([{'conditions': {'ready': False}}], False, False),
                                              ([{'conditions': {'ready': True}}], False, True)):
                value = json.dumps({'items': [{'endpoints': endpoints}]})
                stub = f"ksys() {{ printf '%s' '{value}'; }};"
                for command, expected in (('wait_backend_removed', removed), ('wait_backend_ready', ready)):
                    with self.subTest(lab=lab, command=command, endpoints=endpoints):
                        result = exercise(lab, command, stub)
                        self.assertEqual(result.returncode == 0, expected, result.stderr)

    def test_secret_wait_claims_a_change_only_after_reading_it(self):
        for stub, success in (('k() { return 1; };', False),
                              ('k() { echo old-value; };', False),
                              ('k() { echo rotated-lab30; };', True)):
            with self.subTest(stub=stub):
                result = exercise(30, 'wait_secret rotated-lab30', stub)
                self.assertEqual(result.returncode == 0, success)
                self.assertEqual('observed after' in result.stdout, success)

    def test_api_readiness_alone_does_not_confirm_a_new_static_pod_flag(self):
        for arguments, expected in ((['kube-apiserver'], False),
                                    (['kube-apiserver', '--profiling=false'], True)):
            value = json.dumps({'spec': {'containers': [{'command': arguments}]}})
            stub = f"k() {{ if [[ $1 == get ]]; then echo ok; else printf '%s' '{value}'; fi; }};"
            with self.subTest(arguments=arguments):
                result = exercise(27, 'wait_profiling false', stub)
                self.assertEqual(result.returncode == 0, expected)
                self.assertEqual('observed after' in result.stdout, expected)
        result = exercise(27, 'wait_profiling default', 'k() { return 1; };')
        self.assertNotEqual(result.returncode, 0)

    def test_network_probe_exit_zero_without_http_200_is_not_recovery(self):
        for response, expected in (('failed TimeoutError', False), ('ok status=200', True)):
            with self.subTest(response=response):
                result = exercise(31, 'wait_network_recovery', f"probe() {{ echo '{response}'; }};")
                self.assertEqual(result.returncode == 0, expected)

    def test_startup_error_invalidates_previous_completed_sample(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            workspace = home / 'labs/lab12'
            workspace.mkdir(parents=True)
            (workspace / 'restored-complete.txt').write_text('3\n')
            (workspace / 'runs-restored.txt').write_text('run=1 success=1\n' * 3)
            (workspace / 'run.sh').write_text('echo failed >&2\nexit 1\n')
            result = exercise(12, 'trial restored 3', home=home)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((workspace / 'restored-complete.txt').exists())
            result = exercise(12, 'startup_summary', home=home)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('healthy sample:', result.stdout)

    def test_completed_startup_misses_count_in_the_sample(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            workspace = home / 'labs/lab12'
            workspace.mkdir(parents=True)
            (workspace / 'run.sh').write_text('''mkdir -p diagnostics metrics
for n in 1 2 3; do
  echo '{"trial":{"success":0},"pod":{},"service":{},"events":{"items":[]},"endpointslices":{"items":[]}}' > "diagnostics/run-$n.json"
  echo "run=$n success=0 elapsed=30.000s"
done
echo 'ce_start_success 0' > metrics/start.prom
''')
            result = exercise(12, 'trial restored 3', home=home)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((workspace / 'evidence-restored-3.json').exists())
            result = exercise(12, 'startup_summary', home=home)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('0/3 = 0.000', result.stdout)


if __name__ == '__main__':
    unittest.main()
