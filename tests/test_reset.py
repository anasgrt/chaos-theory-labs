"""Run Ansible cleanup for real; fake only the external container runtime."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('ansible-playbook'), 'Ansible is required for reset integration')
class ResetTests(unittest.TestCase):
    def test_reset_is_scoped_idempotent_and_preserves_evidence_on_failure(self):
        with tempfile.TemporaryDirectory(prefix='chaos-reset-') as directory:
            root = Path(directory)
            paths = ['labs/lab04/marker', 'labs/lab07/marker',
                     'labs/lab08/marker', 'labs/versions.txt', 'labs/.provisioned',
                     'containers/ce-lab07-exec', 'containers/ce-lab08-original',
                     'volumes/ce-lab08-data', 'volumes/other-data',
                     'rke2/server/db/marker', 'rancher/bootstrap-password', '.kube/rke2.yaml']
            for number in ('03', '04', '05', '09', '10', '11', '13', '14', '15', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26'):
                paths += [f'clusters/lab{number}', f'labs/lab{number}/kubeconfig']
            for name in paths:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('preserve this exact content\n')
            binary = root / 'bin'
            binary.mkdir()
            stubs = {
                'kubectl': '#!/bin/sh\necho "API is broken; reset must not call kubectl" >&2\nexit 90\n',
                'kind': '''#!/usr/bin/env bash
set -euo pipefail
case "$1 $2" in
  'get clusters') find "$RESET_FIXTURE/clusters" -type f -printf '%f\\n' ;;
  'delete cluster')
    [[ "$3" == --name && "$5" == --kubeconfig ]]
    [[ "$6" == "$RESET_FIXTURE/labs/$4/kubeconfig" ]]
    [[ ${FAIL_DELETE:-0} != 1 ]] || exit 8
    rm "$RESET_FIXTURE/clusters/$4"
    ;;
  *) exit 99 ;;
esac
''',
                'docker': '''#!/usr/bin/env bash
set -euo pipefail
case "$*" in
  "ps -aq --filter name=^/ce-lab08-")
    find "$RESET_FIXTURE/containers" -type f -name 'ce-lab08-*' -printf '%f\\n' ;;
  'rm -f ce-lab08-original') rm "$RESET_FIXTURE/containers/ce-lab08-original" ;;
  'volume ls --format {{.Name}} --filter name=ce-lab08-data')
    find "$RESET_FIXTURE/volumes" -type f -name ce-lab08-data -printf '%f\\n' ;;
  'volume rm ce-lab08-data') rm "$RESET_FIXTURE/volumes/ce-lab08-data" ;;
  *) echo "Unexpected Docker operation: $*" >&2; exit 99 ;;
esac
''',
            }
            for name, source in stubs.items():
                (binary / name).write_text(source)
                (binary / name).chmod(0o755)
            result = subprocess.run(
                ['ansible-playbook', '-i', 'localhost,', str(ROOT / 'tests/ansible/reset.yml'),
                 '-e', f'reset_fixture={root}', '-e', 'ansible_become=false'],
                env=dict(os.environ, ANSIBLE_CONFIG=str(ROOT / 'ansible/ansible.cfg')),
                capture_output=True, text=True, timeout=300,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual({p.name for p in (root / 'clusters').iterdir()}, {'lab04'})
            self.assertEqual({p.name for p in (root / 'containers').iterdir()}, {'ce-lab07-exec'})
            self.assertEqual({p.name for p in (root / 'volumes').iterdir()}, {'other-data'})
            self.assertEqual((root / 'labs/lab04/marker').read_text(), 'preserve this exact content\n')
            for name in ('rke2/server/db/marker', 'rancher/bootstrap-password', '.kube/rke2.yaml'):
                self.assertEqual((root / name).read_text(), 'preserve this exact content\n')


if __name__ == '__main__':
    unittest.main()
