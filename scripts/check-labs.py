#!/usr/bin/env python3
"""Validate teaching content, rendering and embedded program syntax (no injection)."""
import ast
import re
import subprocess
import sys

import yaml
from lab_content import ROOT, Loader, fixture_path, load_labs, render_card


def check_shell(source, label):
    result = subprocess.run(['bash', '-n'], input=source, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f'{label}: {result.stderr}')
    # Also inspect programs embedded in shell heredocs; bash -n treats them as text.
    lines = source.splitlines()
    for index, line in enumerate(lines):
        match = re.search(r"<<\s*['\"]?([A-Z][A-Z0-9_]*)['\"]?\s*$", line)
        if not match:
            continue
        delimiter = match.group(1)
        end = next((i for i in range(index + 1, len(lines)) if lines[i] == delimiter), None)
        if end is None:
            raise ValueError(f'{label}: unterminated {delimiter} heredoc')
        body = '\n'.join(lines[index + 1:end]) + '\n'
        if delimiter.startswith('PY'):
            ast.parse(body, filename=f'{label}:{delimiter}')
        elif delimiter in ('SH', 'BASH'):
            check_shell(body, f'{label}:{delimiter}')
        elif delimiter in ('YAML', 'YML'):
            list(yaml.safe_load_all(body))


def main():
    labs = load_labs()
    theory = (ROOT / 'docs/chaos-theory.md').read_text(encoding='utf-8')
    blocks = 0
    for number, lab in labs.items():
        sections = lab['task']['brief'].get('theory_sections', [])
        if number in ('10', '11', '12', '13', '14', '17', '18', '19', '20', '21') and not sections:
            raise ValueError(f'Lab {number}: missing precise container/Kubernetes theory mapping')
        for section in sections:
            if not re.search(r'^#{2,4} ' + re.escape(section) + r'\s', theory, re.MULTILINE):
                raise ValueError(f'Lab {number}: theory section {section} does not exist')
        question = render_card(number, lab, 'question')
        solution = render_card(number, lab, 'solution')
        for paragraph in lab['task']['brief']['theory']:
            if ' '.join(paragraph.split()) not in ' '.join(question.split()):
                raise ValueError(f'Lab {number}: theory missing from question')
        for answer in lab['solution']:
            if ' '.join(answer.split()) in ' '.join(question.split()):
                raise ValueError(f'Lab {number}: solution leaked into question')
            if ' '.join(answer.split()) not in ' '.join(solution.split()):
                raise ValueError(f'Lab {number}: worked answer missing from solution')
        for step in lab['commands']:
            if step['run'].strip() not in question or step['run'].strip() not in solution:
                raise ValueError(f'Lab {number}: incomplete command reference')
            if any(' '.join(step['record'].split()) not in ' '.join(card.split()) for card in (question, solution)):
                raise ValueError(f'Lab {number}: step lacks its evidence instruction')
        if lab['transfer_solution'] not in ' '.join(solution.split()):
            raise ValueError(f'Lab {number}: understanding answer missing')
        for group in ('commands', 'fallback', 'setup', 'verify', 'reset'):
            for index, command in enumerate(lab.get(group, []), 1):
                key = 'run' if group in ('commands', 'fallback') else 'command'
                check_shell(command[key], f'{number}/{group}/{index}')
                blocks += 1
        for name in lab.get('files', []):
            path = fixture_path(number, name)
            if not path.is_file():
                raise ValueError(f'Lab {number}: invalid fixture path {name}')
            if path.suffix in ('.yaml', '.yml'):
                for resource in yaml.safe_load_all(path.read_text(encoding='utf-8')):
                    if not isinstance(resource, dict) or not all(key in resource for key in ('apiVersion', 'kind', 'metadata')):
                        raise ValueError(f'Lab {number}: invalid Kubernetes resource in {name}')
                    spec = resource.get('spec', {})
                    pod_spec = spec if resource['kind'] == 'Pod' else spec.get('template', {}).get('spec', {})
                    for container in pod_spec.get('containers', []) + pod_spec.get('initContainers', []):
                        command = container.get('command', []) + container.get('args', [])
                        if command and command[0].startswith('python') and '-c' in command:
                            ast.parse(command[command.index('-c') + 1], filename=name)
    shell_files = list(ROOT.glob('*.sh'))
    for directory in ('ansible', 'labs', 'scripts', 'tests'):
        shell_files.extend((ROOT / directory).rglob('*.sh'))
    for path in shell_files:
        check_shell(path.read_text(encoding='utf-8'), str(path.relative_to(ROOT)))
    for path in (ROOT / 'labs').rglob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    for path in (ROOT / 'ansible').rglob('*.yml'):
        yaml.load(path.read_text(encoding='utf-8'), Loader=Loader)
    subprocess.run([sys.executable, str(ROOT / 'scripts/render-labs.py'), '--check'], check=True)
    print(f'Validated {len(labs)} labs, {len(labs) * 2} cards and {blocks} shell blocks; embedded Python/YAML and fixture syntax passed.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, SyntaxError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc))
