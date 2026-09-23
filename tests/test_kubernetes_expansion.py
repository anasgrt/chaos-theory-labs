"""Check causal comparisons and evidence handling in Labs 23–26."""
import base64
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]


def asset(lab, name):
    return next((ROOT / 'labs').glob(f'{lab}-*/files/{name}'))


def module(lab, name):
    spec = importlib.util.spec_from_file_location(f'lab{lab}_{name}', asset(lab, name))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def manifest(lab, name):
    return yaml.safe_load(asset(lab, name).read_text())


server = module('23', 'server.py')
prepare = module('26', 'prepare.py')
storage = module('26', 'storage_probe.py')


class ProbeComparisonTests(unittest.TestCase):
    def test_readiness_fault_preserves_application_and_liveness(self):
        with patch.object(server.Path, 'exists', lambda path: str(path) == '/tmp/unready'):
            self.assertEqual(server.response('/readyz')[0], 503)
            self.assertEqual(server.response('/livez')[0], 200)
            self.assertEqual(server.response('/')[0], 200)

    def test_progress_fault_affects_real_requests_and_both_health_checks(self):
        with patch.object(server.Path, 'exists', lambda path: str(path) == '/tmp/stalled'):
            for path in ('/', '/livez', '/readyz'):
                self.assertEqual(server.response(path)[0], 503)
            self.assertEqual(server.response('/started')[0], 200)

    def test_restart_comparison_changes_only_startup_protection(self):
        protected = manifest('23', 'protected.yaml')
        del protected['spec']['containers'][0]['startupProbe']
        self.assertEqual(protected, manifest('23', 'no-startup.yaml'))


class StorageAndBudgetTests(unittest.TestCase):
    def test_consumer_conflict_is_only_placement_and_matches_actual_pv(self):
        good = manifest('24', 'consumer.yaml')
        bad = manifest('24', 'wrong-node.yaml')
        volume = manifest('24', 'volume.yaml')['spec']
        nodes = volume['nodeAffinity']['required']['nodeSelectorTerms'][0]['matchExpressions'][0]['values']
        self.assertIn(good['spec']['nodeSelector']['kubernetes.io/hostname'], nodes)
        self.assertNotIn(bad['spec']['nodeSelector']['kubernetes.io/hostname'], nodes)
        bad['spec']['nodeSelector'] = good['spec']['nodeSelector']
        self.assertEqual(good, bad)
        self.assertEqual(volume['persistentVolumeReclaimPolicy'], 'Retain')
        self.assertEqual(manifest('24', 'storage-class.yaml')['volumeBindingMode'], 'WaitForFirstConsumer')

    def test_limit_fault_fits_remaining_quota_and_breaks_only_memory_limit(self):
        quota = manifest('25', 'quota.yaml')['spec']['hard']
        baseline = manifest('25', 'baseline.yaml')['spec']['containers'][0]['resources']
        oversized = manifest('25', 'oversized.yaml')['spec']['containers'][0]['resources']
        limits = manifest('25', 'defaults.yaml')['spec']['limits'][0]
        self.assertEqual(oversized['requests'], baseline['requests'])
        self.assertEqual(int(quota['requests.cpu'][:-1]), 2 * int(oversized['requests']['cpu'][:-1]))
        self.assertLess(2 * int(oversized['requests']['memory'][:-2]), int(quota['requests.memory'][:-2]))
        self.assertGreater(int(oversized['limits']['memory'][:-2]), int(limits['max']['memory'][:-2]))
        self.assertNotIn('resources', manifest('25', 'defaulted.yaml')['spec']['containers'][0])
        self.assertEqual(limits['defaultRequest'], baseline['requests'])


class EncryptionEvidenceTests(unittest.TestCase):
    def original(self):
        return {'spec': {'containers': [{'name': 'kube-apiserver',
                'image': 'unchanged', 'command': ['kube-apiserver', '--secure-port=6443'],
                'volumeMounts': [{'name': 'certs', 'mountPath': '/certs'}]}],
                'volumes': [{'name': 'certs', 'hostPath': {'path': '/certs'}}], 'hostNetwork': True}}

    def test_generated_providers_use_distinct_valid_keys_and_preserve_api_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            original = self.original()
            (workspace / 'apiserver-observed.json').write_text(json.dumps(original))
            prepare.prepare(workspace)
            keys = []
            for mode in ('key1', 'key2'):
                provider = json.loads((workspace / f'provider-{mode}.json').read_text())
                rule = provider['resources'][0]
                self.assertEqual(rule['resources'], ['secrets'])
                self.assertEqual(rule['providers'][1], {'identity': {}})
                key = rule['providers'][0]['aescbc']['keys'][0]
                keys.append(base64.b64decode(key['secret'], validate=True))
                self.assertEqual(len(keys[-1]), 32)
                self.assertEqual(key['name'], f'lab-{mode}')
                pod = json.loads((workspace / f'apiserver-{mode}.json').read_text())
                actual = copy.deepcopy(pod['spec'])
                self.assertEqual(actual['containers'][0]['command'].pop(),
                                 f'--encryption-provider-config=/etc/kubernetes/ce-lab26/provider-{mode}.json')
                actual['containers'][0]['volumeMounts'].pop()
                actual['volumes'].pop()
                self.assertEqual(actual, original['spec'])
            self.assertNotEqual(keys[0], keys[1])
            self.assertEqual(json.loads((workspace / 'apiserver-observed.json').read_text()), original)

    def test_refuses_to_replace_an_existing_encryption_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            original = self.original()
            original['spec']['containers'][0]['command'].append('--encryption-provider-config=/existing')
            (workspace / 'apiserver-observed.json').write_text(json.dumps(original))
            with self.assertRaisesRegex(ValueError, 'already configures encryption'):
                prepare.prepare(workspace)
            self.assertFalse((workspace / 'provider-key1.json').exists())

    def test_storage_read_preserves_exact_binary_and_requests_only_the_named_record(self):
        raw = b'k8s:enc:aescbc:v1:lab-key1:\x00\xff\n'
        outputs = [subprocess.CompletedProcess([], 0, stdout='etcd-id\n'),
                   subprocess.CompletedProcess([], 0, stdout=json.dumps({'kvs': [{'value': base64.b64encode(raw).decode()}]}))]
        with patch.object(storage.subprocess, 'run', side_effect=outputs) as run:
            self.assertEqual(storage.read_record('fresh'), raw)
        self.assertIn('/registry/secrets/ce-lab26/fresh', run.call_args.args[0])
        self.assertIn('prefix=k8s:enc:aescbc:v1:lab-key1:', storage.describe(raw))
        self.assertIn('demo_password_visible=False', storage.describe(raw))
        self.assertIn('demo_password_visible=True', storage.describe(b'k8s\x00' + storage.MARKER))

    def test_missing_record_and_failed_etcd_read_cannot_look_like_plaintext(self):
        outputs = [subprocess.CompletedProcess([], 0, stdout='etcd-id\n'),
                   subprocess.CompletedProcess([], 0, stdout='{"count":0}')]
        with patch.object(storage.subprocess, 'run', side_effect=outputs):
            with self.assertRaisesRegex(ValueError, 'not found'):
                storage.read_record('legacy')
        with patch.object(storage.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'docker')):
            with self.assertRaises(subprocess.CalledProcessError):
                storage.read_record('legacy')


if __name__ == '__main__':
    unittest.main()
