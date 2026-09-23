"""Hosts reconciliation tests never modify real hosts files or certificate trust."""
import importlib.util
import os
import subprocess
import sys
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


def make_ca(directory, name, common='Chaos Labs Rancher CA'):
    """A real self-signed CA, so digests come from certificates, not fixtures."""
    key, crt = directory / (name + '.key'), directory / (name + '.crt')
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                    '-keyout', str(key), '-out', str(crt), '-days', '2',
                    '-subj', '/CN=' + common], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return crt


class SupersededCertificateTests(unittest.TestCase):
    """Recreating a VM mints a new CA under the same name; the old one lingers."""

    def test_digests_match_openssl_for_a_real_certificate(self):
        with tempfile.TemporaryDirectory(prefix='browser-ca-') as tmp:
            crt = make_ca(Path(tmp), 'current')
            sha1, sha256 = browser.certificate_digests(crt.read_text())
            for algorithm, expected in (('sha1', sha1), ('sha256', sha256)):
                der = subprocess.run(['openssl', 'x509', '-in', str(crt), '-outform', 'der'],
                                     check=True, capture_output=True).stdout
                digest = subprocess.run(['openssl', 'dgst', '-' + algorithm],
                                        input=der, check=True, capture_output=True).stdout
                self.assertIn(expected.lower(), digest.decode().strip().lower())

    def test_only_certificates_other_than_the_current_one_are_superseded(self):
        with tempfile.TemporaryDirectory(prefix='browser-stale-') as tmp:
            directory = Path(tmp)
            current, old, older = (make_ca(directory, name) for name in ('current', 'old', 'older'))
            bundle = old.read_text() + current.read_text() + older.read_text()
            stale = browser.superseded_certificates(bundle, current.read_text())
            self.assertEqual(stale, [browser.certificate_digests(old.read_text())[0],
                                     browser.certificate_digests(older.read_text())[0]])
            self.assertNotIn(browser.certificate_digests(current.read_text())[0], stale)

    def test_nothing_is_superseded_when_only_the_current_ca_is_trusted(self):
        with tempfile.TemporaryDirectory(prefix='browser-clean-') as tmp:
            current = make_ca(Path(tmp), 'current')
            self.assertEqual(browser.superseded_certificates(current.read_text(), current.read_text()), [])
            self.assertEqual(browser.superseded_certificates('', current.read_text()), [])
            # A duplicate listing of the same certificate is not a second CA.
            self.assertEqual(
                browser.superseded_certificates(current.read_text() * 2, current.read_text()), [])

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS keychain tooling required')
    def test_pruning_automatically_removes_only_the_old_ca(self):
        with tempfile.TemporaryDirectory(prefix='browser-keychain-') as tmp:
            directory = Path(tmp)
            current, old = make_ca(directory, 'current'), make_ca(directory, 'old')
            unrelated = make_ca(directory, 'unrelated', common='Someone Else CA')
            keychain = str(directory / 'probe.keychain')
            subprocess.run(['security', 'create-keychain', '-p', 'probepass', keychain], check=True)
            self.addCleanup(subprocess.run, ['security', 'delete-keychain', keychain])
            for certificate in (current, old, unrelated):
                subprocess.run(['security', 'import', str(certificate), '-k', keychain, '-A'],
                               check=True, stdout=subprocess.DEVNULL)

            removed = browser.prune_superseded_cas(current, keychain)
            self.assertEqual(removed, [browser.certificate_digests(old.read_text())[0]])
            listed = subprocess.run(['security', 'find-certificate', '-c', 'Chaos Labs Rancher CA',
                                     '-a', '-p', keychain], check=True, capture_output=True, text=True)
            remaining = browser.pem_certificates(listed.stdout)
            self.assertEqual(len(remaining), 1)
            self.assertEqual(browser.certificate_digests(remaining[0]),
                             browser.certificate_digests(current.read_text()))
            # A certificate with another name is never touched.
            other = subprocess.run(['security', 'find-certificate', '-c', 'Someone Else CA',
                                    '-a', '-p', keychain], check=True, capture_output=True, text=True)
            self.assertEqual(len(browser.pem_certificates(other.stdout)), 1)
            # Running again has nothing left to do.
            self.assertEqual(browser.prune_superseded_cas(current, keychain), [])


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
