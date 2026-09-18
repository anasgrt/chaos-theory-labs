#!/usr/bin/env python3
"""Render the learner guide from the lab definitions; --check detects drift."""
import argparse
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

class Loader(yaml.SafeLoader):
    pass

Loader.add_constructor('!unsafe', lambda loader, node: loader.construct_scalar(node))

def render():
    labs = [(p.stem[:2], yaml.load(p.read_text(), Loader=Loader))
            for p in sorted((ROOT / 'ansible/labs').glob('[0-9][0-9]-*.yml'))]
    parts = ['''# Chaos labs — understand the result

Each lab connects one question to a controlled comparison. Read the theory, predict the result, run the core procedure, and explain your observations before opening the solution. The explanations come from `chaos-theory.md`; the commands adapt them to this repository's fixtures.

## Start here

1. From the Mac project folder, run `./up.sh` and complete Lab 00.
2. Prepare the chosen lab with `./ansible/run-lab.sh NN setup`, then check its baseline with `./ansible/run-lab.sh NN verify`. Setup prepares the fixture and supporting programs; it does not inject the fault. Rerunning setup resets the fixture.
3. Read `./ansible/run-lab.sh NN question`, which includes the core commands. Use `vagrant ssh` for the named VM terminals. Run commands in Bash without exit-on-error: some failures are deliberate observations.
4. Record your prediction, observed comparison and explanation. Then open the solution or run `./ansible/run-lab.sh NN solution`. Finish recovery and any optional work before `./ansible/run-lab.sh NN reset` on the Mac.

Stop if the baseline fails. A setup error, failed injector or missing measurement is not evidence of resilience. If the outcome differs from your prediction, check that the fault took effect and that recovery passed; report the result you actually observed. Expected timings and counts are not guarantees.

Use only the named targets in the disposable VM, one fault at a time. Keep another VM terminal available for cleanup. A stopped injector does not always remove its effect; use each lab's recovery procedure. Lab 00 establishes a snapshot as a fallback.

**Dependencies:** Labs 11–13 require Lab 10's `chaos` cluster. Lab 08 setup stops Lab 07's stack because both use port 8080. Lab 14 uses a separate `ha` cluster: remove `chaos` and allocate at least 16 GiB VM memory first, as described in README.md. Lab 16 is design only. Other labs use the shared Lab 00 environment.

**A complete answer:** what changed → the evidence → why the mechanism explains it → whether recovery passed. Use your own numbers and outputs. Optional comparisons are not completion requirements. Prepared scripts remain readable under `~/labs/labNN/`; understanding their implementation is optional unless it is the subject of the question.

## Labs

''']
    for num, d in labs:
        parts.append(f'- [Lab {num}: {d["title"].split(" — ", 1)[1]}](#lab-{num})\n')

    def commands(items, expectations=False):
        for index, c in enumerate(items, 1):
            parts.append(f'**{index}. {c["name"]}** — {c.get("where", "VM terminal 1")}\n\n')
            parts.append('```bash\n' + c['run'].rstrip() + '\n```\n\n')
            if expectations and c.get('expect'):
                parts.append('Expected observation: ' + c['expect'] + '\n\n')

    for num, d in labs:
        t = d['task']; b = t['brief']
        parts.append(f'\n<a id="lab-{num}"></a>\n\n## {d["title"]}\n\n**Question:** {t["question"]}\n\n')
        parts.append('\n\n'.join(b['theory']) + '\n\n')
        parts.append('**Source:** ' + b['theory_source'] + '\n\n')
        parts.append('**In this lab:** ' + ' '.join(b['in_this_lab']) + '\n\n')
        parts.append('**Predict:** ' + t['predict'] + '\n\n')
        parts.append('\n'.join(f'{i}. {s}' for i, s in enumerate(t['steps'], 1)) + '\n\n')
        parts.append('**Explain the result:** ' + t['answer_with'] + '\n\n')
        parts.append('<details>\n<summary>Core procedure — run after predicting</summary>\n\n')
        parts.append(f'Run `./ansible/run-lab.sh {num} setup` and `verify` on the Mac first. Use the named terminals and keep the same shell when blocks reuse variables. Fallback blocks are only for failed cleanup.\n\n')
        commands(d['commands'])
        parts.append('**Recovery check:** ' + d['verify_note'] + '\n\n</details>\n\n')
        parts.append('<details>\n<summary>Solution — compare after explaining your result</summary>\n\n' + d['solution'] + '\n\n')
        parts.append('Expected patterns below are conditional on a working baseline and a successful injection. Record differences; do not substitute these patterns for your measurements.\n\n')
        for i, c in enumerate(d['commands'], 1):
            if c.get('expect'):
                parts.append(f'**Step {i}:** {c["expect"]}\n\n')
        parts.append('</details>\n\n')
        if d.get('optional_commands'):
            parts.append('<details>\n<summary>Optional comparison — beyond the core question</summary>\n\n' + d['optional_explanation'] + '\n\n')
            commands(d['optional_commands'], expectations=True)
            parts.append('</details>\n\n')
        parts.append(f'After recovery and any optional work, reset from the Mac: `./ansible/run-lab.sh {num} reset`.\n')
    parts.append('''
## Source and verification

Edit `ansible/labs/*.yml`, then regenerate this guide with `python3 scripts/render-labs.py`. The terminal cards use those same definitions. `chaos-theory.md` remains the detailed reference; source citations use the original section numbers retained in that file rather than its renumbered chapter headings.

Local validation checks document consistency, rendering and command syntax. It does not establish live Ubuntu, Docker or Kubernetes outcomes. A successful experiment supports only the conditions and measurements actually tested.
''')
    return ''.join(parts)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    target = ROOT / 'chaos-labs.md'
    content = render()
    if args.check:
        if not target.exists() or target.read_text() != content:
            parser.exit(1, 'chaos-labs.md is stale; run scripts/render-labs.py\n')
        print('Guide matches all lab definitions.')
    else:
        target.write_text(content)
        print('Rendered chaos-labs.md from 17 lab definitions.')
