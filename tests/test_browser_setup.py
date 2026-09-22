"""Hosts reconciliation tests never modify real hosts files or certificate trust."""
import importlib.util
import os
import subprocess
import tempfile
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('browser_setup', Path(__file__).resolve().parents[1] / 'scripts/setup-browser.py')
browser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser)


class BrowserHostsTests(unittest.TestCase):
    def test_missing_mapping_is_added_and_repeated_run_is_identical(self):
        original = '# Host Database\n127.0.0.1 localhost\n'
        updated = browser.update_hosts(original, '192.168.56.10', 'rancher.chaos.test')
        self.assertEqual(updated, original + '192.168.56.10 rancher.chaos.test\n')
        self.assertEqual(browser.update_hosts(updated, '192.168.56.10', 'rancher.chaos.test'), updated)

    def test_stale_and_duplicate_entries_preserve_unrelated_aliases_and_comments(self):
        original = ('127.0.0.1 localhost\n'
                    '192.0.2.1 rancher.chaos.test other.test # shared\n'
                    '192.0.2.2 RANCHER.CHAOS.TEST # old address\n'
                    '# rancher.chaos.test is a lab name\n')
        updated = browser.update_hosts(original, '192.168.56.10', 'rancher.chaos.test')
        self.assertEqual(updated, '127.0.0.1 localhost\n192.0.2.1\tother.test # shared\n'
                         '# old address\n# rancher.chaos.test is a lab name\n'
                         '192.168.56.10 rancher.chaos.test\n')
        self.assertEqual(browser.update_hosts(updated, '192.168.56.10', 'rancher.chaos.test'), updated)

    def test_configuration_is_not_hardcoded_and_missing_newline_is_handled(self):
        self.assertEqual(browser.update_hosts('127.0.0.1 localhost', '192.168.57.20', 'custom.lab.test'),
                         '127.0.0.1 localhost\n192.168.57.20 custom.lab.test\n')

    def test_invalid_configuration_cannot_inject_hosts_lines(self):
        for ip, name in [('::1', 'rancher.test'), ('invalid', 'rancher.test'),
                         ('192.168.56.10', 'rancher.test\n127.0.0.1 other.test'),
                         ('192.168.56.10', '$(touch injected)')]:
            with self.subTest(ip=ip, name=name), self.assertRaises(ValueError):
                browser.update_hosts('127.0.0.1 localhost\n', ip, name)


class BrowserCommandTests(unittest.TestCase):
    def test_lab_command_routes_to_helper_from_another_directory(self):
        with tempfile.TemporaryDirectory(prefix='browser routing ') as tmp:
            directory = Path(tmp)
            python = directory / 'python3'
            python.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            python.chmod(0o755)
            result = subprocess.run(['bash', str(browser.ROOT / 'lab.sh'), 'browser-setup'],
                                    cwd=tmp, env=dict(os.environ, PATH=tmp + os.pathsep + os.environ['PATH']),
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(browser.ROOT / 'scripts/setup-browser.py'))
            rejected = subprocess.run(['bash', str(browser.ROOT / 'lab.sh'), 'browser-setup', 'extra'],
                                      cwd=tmp, capture_output=True, text=True)
            self.assertNotEqual(rejected.returncode, 0)
