"""Recorded PIDs must identify this lab before cleanup sends a signal."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lab_content import load_labs


@unittest.skipUnless(Path('/proc/self/exe').exists(), 'Linux process identity is required')
class ProcessResetTests(unittest.TestCase):
    def check_reset(self, number, filename, own_command, foreign_command, home):
        workspace = home / 'labs' / f'lab{number}'
        source = load_labs()[number]['reset'][0]['command']
        env = dict(os.environ, HOME=str(home))
        for command, owned in ((foreign_command, False), (own_command, True)):
            process = subprocess.Popen(command, stdin=subprocess.PIPE)
            try:
                (workspace / filename).write_text(str(process.pid))
                subprocess.run(['bash', '-euo', 'pipefail', '-c', source], env=env,
                               check=True, capture_output=True, text=True, timeout=10)
                if owned:
                    process.wait(timeout=5)
                else:
                    self.assertIsNone(process.poll(), 'Reset killed a process owned by another lab')
                self.assertFalse((workspace / filename).exists())
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
                process.stdin.close()

    def test_port_forward_reset_checks_the_private_kubeconfig(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            workspace = home / 'labs/lab04'
            workspace.mkdir(parents=True)
            stub = home / 'forward.sh'
            stub.write_text("trap 'exit 0' TERM\nwhile :; do read -r -t 1 line; done\n")
            def command(number):
                return ['bash', str(stub), f'--kubeconfig={home}/labs/lab{number}/kubeconfig',
                        f'--context=kind-lab{number}', 'port-forward', 'pod/goldpinger-slow']
            self.check_reset('04', 'lab04-port-forward.pid', command('04'), command('03'), home)


if __name__ == '__main__':
    unittest.main()
