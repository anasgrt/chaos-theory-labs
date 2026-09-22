"""Run the real reset-all discovery and loop against isolated fixtures.

No VM is contacted. The shipped tasks from ansible/reset-all.yml are executed
against a temporary directory tree, with only kind and Docker replaced, so the
discovery command, the per-lab loop and the isolation guarantees under test are
the ones that ship.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]

KIND_STUB = '''#!/usr/bin/env bash
set -euo pipefail
case "$1 $2" in
  'get clusters')
    if [ -d "$RESET_FIXTURE/clusters" ]; then ls -1 "$RESET_FIXTURE/clusters"; fi ;;
  'delete cluster')
    [[ "$3" == --name && "$5" == --kubeconfig ]]
    [[ "$6" == "$RESET_FIXTURE/labs/$4/kubeconfig" ]]
    rm -f "$RESET_FIXTURE/clusters/$4" ;;
  *) exit 99 ;;
esac
'''

DOCKER_STUB = '''#!/usr/bin/env bash
set -euo pipefail
case "$*" in
  "ps -aq --filter name=^/ce-lab08-")
    if [ -d "$RESET_FIXTURE/containers" ]; then
      ls -1 "$RESET_FIXTURE/containers" | grep '^ce-lab08-' || true
    fi ;;
  'rm -f ce-lab08-original') rm -f "$RESET_FIXTURE/containers/ce-lab08-original" ;;
  'volume ls --format {{.Name}} --filter name=ce-lab08-data')
    if [ -d "$RESET_FIXTURE/volumes" ]; then
      ls -1 "$RESET_FIXTURE/volumes" | grep '^ce-lab08-data$' || true
    fi ;;
  'volume rm ce-lab08-data') rm -f "$RESET_FIXTURE/volumes/ce-lab08-data" ;;
  *) echo "Unexpected Docker operation: $*" >&2; exit 99 ;;
esac
'''


def reset_all_tasks():
    """The shipped play, with the interactive confirmation left in place."""
    return yaml.safe_load((ROOT / 'ansible/reset-all.yml').read_text())[0]['tasks']


def build_fixture(root, workspaces, clusters, containers=()):
    (root / 'labs').mkdir(parents=True, exist_ok=True)
    for name in workspaces:
        (root / 'labs' / name).mkdir(parents=True, exist_ok=True)
        (root / 'labs' / name / 'kubeconfig').write_text('preserve this exact content\n')
        (root / 'labs' / name / 'results.txt').write_text('preserve this exact content\n')
    for keep in ('versions.txt', '.provisioned', 'chaos-labs.md'):
        (root / 'labs' / keep).write_text('preserve this exact content\n')
    for name in clusters:
        (root / 'clusters').mkdir(parents=True, exist_ok=True)
        (root / 'clusters' / name).write_text('cluster\n')
    for name in containers:
        (root / 'containers').mkdir(parents=True, exist_ok=True)
        (root / 'containers' / name).write_text('container\n')
    (root / 'volumes').mkdir(parents=True, exist_ok=True)
    (root / 'volumes' / 'other-data').write_text('preserve this exact content\n')
    # Shared platform state that no reset may ever touch.
    for name in ('rke2/server/db/marker', 'rancher/bootstrap-password', '.kube/rke2.yaml'):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('preserve this exact content\n')
    binary = root / 'bin'
    binary.mkdir(exist_ok=True)
    for name, source in (('kind', KIND_STUB), ('docker', DOCKER_STUB)):
        (binary / name).write_text(source)
        (binary / name).chmod(0o755)


def run_reset_all(root, extra_vars=None, expect_success=True):
    # Written beside the real playbook so "tasks/reset-one.yml" and the
    # controller-side lab lookup resolve exactly as they do in production.
    playbook = ROOT / 'ansible' / ('.reset-all-under-test-%s.yml' % root.name)
    playbook.write_text(yaml.safe_dump([{
        'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
        'environment': {
            'PATH': '%s:%s' % (root / 'bin', os.environ['PATH']),
            'RESET_FIXTURE': str(root),
            'HOME': str(root),
        },
        'vars': {
            'lab_root': str(root / 'labs'),
            'reset_all_confirmed': 'yes',
            'ansible_become': False,
        },
        'tasks': reset_all_tasks(),
    }]))
    command = ['ansible-playbook', '-i', 'localhost,', str(playbook)]
    if extra_vars:
        command += ['-e', json.dumps(extra_vars)]
    try:
        result = subprocess.run(
            command,
            env=dict(os.environ, ANSIBLE_CONFIG=str(ROOT / 'ansible/ansible.cfg')),
            capture_output=True, text=True, timeout=600)
    finally:
        playbook.unlink(missing_ok=True)
    output = result.stdout + result.stderr
    if expect_success:
        assert result.returncode == 0, output
    return result, output


@unittest.skipUnless(shutil.which('ansible-playbook'), 'Ansible is required')
class ResetAllTests(unittest.TestCase):
    def test_every_installed_lab_is_removed_and_nothing_else_is_touched(self):
        with tempfile.TemporaryDirectory(prefix='chaos-reset-all-') as tmp:
            root = Path(tmp)
            # 03 and 11 are Kubernetes labs, 08 is a container lab with no
            # cluster, and 09 has a cluster whose workspace is already gone.
            build_fixture(root,
                          workspaces=['lab03', 'lab08', 'lab11'],
                          clusters=['lab03', 'lab09', 'lab11'],
                          containers=['ce-lab08-original', 'ce-lab07-exec'])
            (root / 'volumes' / 'ce-lab08-data').write_text('volume\n')

            _, output = run_reset_all(root)

            self.assertIn('Installed labs to reset: 03, 08, 09, 11', output)
            self.assertFalse((root / 'labs' / 'lab03').exists())
            self.assertFalse((root / 'labs' / 'lab08').exists())
            self.assertFalse((root / 'labs' / 'lab11').exists())
            self.assertEqual(list((root / 'clusters').iterdir()), [])
            # The container lab's own resources go; another lab's do not.
            self.assertEqual({p.name for p in (root / 'containers').iterdir()},
                             {'ce-lab07-exec'})
            self.assertEqual({p.name for p in (root / 'volumes').iterdir()},
                             {'other-data'})
            # Shared tooling and the permanent platform survive untouched.
            for name in ('labs/versions.txt', 'labs/.provisioned', 'labs/chaos-labs.md',
                         'rke2/server/db/marker', 'rancher/bootstrap-password',
                         '.kube/rke2.yaml'):
                self.assertEqual((root / name).read_text(), 'preserve this exact content\n', name)

    def test_an_empty_vm_reports_nothing_to_reset_and_changes_nothing(self):
        with tempfile.TemporaryDirectory(prefix='chaos-reset-all-empty-') as tmp:
            root = Path(tmp)
            build_fixture(root, workspaces=[], clusters=[])
            _, output = run_reset_all(root)
            self.assertIn('No installed labs found', output)
            self.assertIn('Nothing to reset.', output)
            self.assertEqual((root / 'labs' / '.provisioned').read_text(),
                             'preserve this exact content\n')

    def test_running_reset_all_twice_is_safe(self):
        with tempfile.TemporaryDirectory(prefix='chaos-reset-all-twice-') as tmp:
            root = Path(tmp)
            build_fixture(root, workspaces=['lab03'], clusters=['lab03'])
            run_reset_all(root)
            _, output = run_reset_all(root)
            self.assertIn('No installed labs found', output)

    def test_a_lab_installed_but_missing_from_the_checkout_fails_clearly(self):
        with tempfile.TemporaryDirectory(prefix='chaos-reset-all-unknown-') as tmp:
            root = Path(tmp)
            # 87 is installed in the VM but has no definition in this checkout.
            build_fixture(root, workspaces=['lab87'], clusters=[])
            result, output = run_reset_all(root, expect_success=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Lab 87 is installed in the VM but has no single definition', output)
            self.assertTrue((root / 'labs' / 'lab87').exists(),
                            'an unknown lab must not be removed by guesswork')

    def test_discovery_ignores_files_and_names_that_are_not_labs(self):
        with tempfile.TemporaryDirectory(prefix='chaos-reset-all-noise-') as tmp:
            root = Path(tmp)
            build_fixture(root, workspaces=['lab03'], clusters=[])
            for noise in ('lab3', 'lab003', 'labXX', 'notalab', 'lab03-backup'):
                (root / 'labs' / noise).mkdir()
            _, output = run_reset_all(root)
            self.assertIn('Installed labs to reset: 03', output)
            for noise in ('lab3', 'lab003', 'labXX', 'notalab', 'lab03-backup'):
                self.assertTrue((root / 'labs' / noise).exists(), noise)


class ResetAllContractTests(unittest.TestCase):
    """The destructive command must confirm, and must not bypass the guards."""

    def setUp(self):
        self.play = yaml.safe_load((ROOT / 'ansible/reset-all.yml').read_text())[0]

    def test_it_confirms_before_changing_anything(self):
        names = [t['name'] for t in self.play['tasks']]
        pause = next(t for t in self.play['tasks'] if 'ansible.builtin.pause' in t)
        confirm = next(t for t in self.play['tasks']
                       if t['name'].startswith('Require an explicit confirmation'))
        self.assertIn("(reset_all_answer.user_input | default('')) | trim == 'reset-all'",
                      confirm['ansible.builtin.assert']['that'])
        for task in (pause, confirm):
            self.assertIn('reset_all_confirmed | length == 0', task['when'])
        # Nothing may be removed before the confirmation is accepted.
        self.assertLess(names.index(confirm['name']), names.index('Reset each installed lab'))

    def test_it_keeps_the_shared_vm_identity_guard(self):
        self.assertIn({'ansible.builtin.include_tasks': 'tasks/identity.yml'},
                      [{k: v} for t in self.play['pre_tasks']
                       for k, v in t.items() if k == 'ansible.builtin.include_tasks'])
        self.assertEqual(self.play['hosts'], 'chaos_labs')

    def test_it_reuses_the_shipped_single_lab_reset(self):
        loop = next(t for t in self.play['tasks'] if t['name'] == 'Reset each installed lab')
        self.assertEqual(loop['ansible.builtin.include_tasks'], 'tasks/reset-one.yml')
        one = yaml.safe_load((ROOT / 'ansible/tasks/reset-one.yml').read_text())
        self.assertEqual(one[-1]['ansible.builtin.include_tasks'], 'reset.yml')


if __name__ == '__main__':
    unittest.main()
