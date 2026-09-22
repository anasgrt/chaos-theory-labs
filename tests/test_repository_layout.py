"""Check discovery, portable entry points and real Ansible file resolution."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import lab_content
from lab_content import fixture_path, lab_paths, load_labs, render_card


class DiscoveryTests(unittest.TestCase):
    def test_document_links_resolve_after_moves(self):
        missing = []
        for document in [ROOT / 'README.md', *(ROOT / 'docs').rglob('*.md')]:
            for href in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)\)', document.read_text(encoding='utf-8')):
                url = urlsplit(href)
                if url.scheme or url.netloc or not url.path:
                    continue
                target = document.parent / unquote(url.path)
                if not target.exists():
                    missing.append(f'{document.relative_to(ROOT)}: broken link {href}')
        self.assertFalse(missing, '\n'.join(missing))

    def test_duplicate_ids_fail_before_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for slug in ('11-first', '11-second'):
                path = root / 'labs' / slug / 'lab.yml'
                path.parent.mkdir(parents=True)
                path.touch()
            with patch.object(lab_content, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'Duplicate lab ID: 11'):
                    lab_paths()

    def test_fixture_paths_cannot_escape_the_lab(self):
        for name in ('../other/file', '/tmp/file', 'folder/file', '..', '', '../lab.yml'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                fixture_path('11', name)

    def test_all_assets_are_owned_and_declared(self):
        for number, lab in load_labs().items():
            directory = lab_paths()[number].parent / 'files'
            actual = {path.name for path in directory.glob('*') if path.is_file()}
            self.assertEqual(actual, set(lab.get('files', [])), f'Unlisted or missing assets in Lab {number}')


@unittest.skipUnless(shutil.which('ansible-playbook'), 'Ansible is required for the layout integration test')
class AnsibleLayoutTests(unittest.TestCase):
    def test_all_cards_and_fixtures_use_the_reorganized_tree(self):
        with tempfile.TemporaryDirectory(prefix='chaos layout ') as directory:
            output = Path(directory)
            env = dict(os.environ, ANSIBLE_CONFIG=str(ROOT / 'ansible/ansible.cfg'))
            result = subprocess.run(
                ['ansible-playbook', '-i', 'localhost,', str(ROOT / 'tests/ansible/layout.yml'),
                 '--extra-vars', json.dumps({'layout_output': str(output)})],
                cwd=directory, env=env, capture_output=True, text=True, timeout=600,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            labs = load_labs()
            self.assertEqual({p.name for p in output.iterdir()}, set(labs))
            for number, lab in labs.items():
                for action in ('question', 'solution'):
                    actual = (output / number / f'{action}.txt').read_text(encoding='utf-8')
                    self.assertEqual(actual, render_card(number, lab, action), f'{number}/{action}')
                for name in lab.get('files', []):
                    self.assertEqual((output / number / name).read_bytes(), fixture_path(number, name).read_bytes())
            listing = subprocess.run(['bash', str(ROOT / 'lab.sh'), 'list'], cwd=directory,
                                     env=env, capture_output=True, text=True, timeout=120)
            self.assertEqual(listing.returncode, 0, listing.stderr)
            self.assertEqual(listing.stdout.splitlines(), [lab['title'] for lab in labs.values()])


if __name__ == '__main__':
    unittest.main()
