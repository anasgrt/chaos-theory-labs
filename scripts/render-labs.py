#!/usr/bin/env python3
"""Render the learner guide from the same definitions as the terminal cards."""
import argparse
from lab_content import ROOT, load_labs


def render():
    labs = load_labs()
    parts = ['''# Chaos labs

Study the theory on each card, predict a result, then run a controlled comparison.
The card explains the mechanisms and measurements needed to answer its question.
[chaos-theory.md](chaos-theory.md) is the deeper reference; citations use its original section numbers.

## Workflow

1. Run `./lab.sh provision` once to prepare the shared VM.
2. Choose any lab. Read `./lab.sh NN question`, then run `./lab.sh NN setup`.
3. Open `./lab.sh ssh`, predict, and run the procedure in its named terminals.
4. Record and explain your results, then compare with `./lab.sh NN solution`.
5. Complete recovery and save any results outside the VM.
6. Run `./lab.sh NN reset` to remove only that lab's resources and files.

All labs use one VM. Each setup supplies its own fixture; Kubernetes labs create
separate named kind clusters inside that VM. No lab requires another lab. Reset
finished labs to free resources. `./lab.sh stop` halts the whole VM and preserves
its files. See [the README](../README.md) for requirements and capacity.

Setup prepares the fixture; the procedure injects the fault. Repeating setup resets
the fixture (Lab 16 preserves your written card). Verify checks readiness before the
experiment; the card's recovery check tests its final state. Stop if the baseline
fails. A missing measurement or an injector that never reached its target is not a pass.

Keep a second shell in the selected VM available for recovery. Run commands in
Bash without `set -e`; some failures are observations. Keep the same shell when
commands reuse variables. Fallback blocks are only for failed recovery. Expected
patterns are not measurements. Kind nodes within a lab share one VM, so they do
not simulate independent physical machines or availability zones.

## Theory to lab map

| Lab | Question | Theory source |
| --- | --- | --- |
''']
    for number, lab in labs.items():
        parts.append(f'| [{number}](#lab-{number}) | {lab["task"]["question"]} | {lab["task"]["brief"]["theory_source"]} |\n')

    def commands(items):
        for index, command in enumerate(items, 1):
            parts.append(f'**{index}. {command["name"]}** — {command.get("where", "VM terminal 1")}\n\n')
            parts.append('```bash\n' + command['run'].rstrip() + '\n```\n\n')

    for number, lab in labs.items():
        task = lab['task']
        brief = task['brief']
        parts.append(f'\n<a id="lab-{number}"></a>\n\n## {lab["title"]}\n\n')
        parts.append(f'**Question:** {task["question"]}\n\n**Before you run:** {lab["prerequisites"]}\n\n')
        parts.append('### Theory you need\n\n' + '\n\n'.join(brief['theory']) + '\n\n')
        parts.append('**Source:** ' + brief['theory_source'] + '\n\n')
        parts.append('**The experiment:** ' + ' '.join(brief['in_this_lab']) + '\n\n')
        parts.append('### How to read the evidence\n\n| Signal | Meaning |\n| --- | --- |\n')
        for reading in brief['readings']:
            parts.append(f'| {reading["signal"]} | {reading["meaning"]} |\n')
        parts.append('\n**Predict:** ' + task['predict'] + '\n\n')
        evidence = task['evidence']
        parts.append('### Record your results\n\n| ' + ' | '.join(evidence['columns']) + ' |\n')
        parts.append('| ' + ' | '.join('---' for _ in evidence['columns']) + ' |\n')
        for row in evidence['rows']:
            parts.append('| ' + row + ' | —' * (len(evidence['columns']) - 1) + ' |\n')
        parts.append('\n### Procedure\n\n')
        commands(lab['commands'])
        parts.append('**Recovery check:** ' + lab['verify_note'] + '\n\n')
        if lab.get('fallback'):
            parts.append('<details>\n<summary>If normal recovery fails</summary>\n\n')
            commands(lab['fallback'])
            parts.append('</details>\n\n')
        parts.append('**Answer:** ' + task['answer_with'] + '\n\n')
        parts.append('**Check your understanding:** ' + task['transfer'] + '\n\n')
        parts.append('<details>\n<summary>Solution — open after writing your answer</summary>\n\n')
        parts.append(lab['solution'] + '\n\n')
        for index, command in enumerate(lab['commands'], 1):
            if command.get('expect'):
                parts.append(f'**Step {index}:** {command["expect"]}\n\n')
        parts.append('**Understanding check:** ' + lab['transfer_solution'] + '\n\n</details>\n\n')
        parts.append(f'After recovery, save results outside the VM, then destroy this lab from the host: `./lab.sh {number} reset`.\n')
    parts.append('''
## Maintaining the labs

Run authoring commands from the repository root. Edit `labs/NN-topic/lab.yml` for
teaching content and inline procedures. Supporting programs live beside it in
`labs/NN-topic/files/` and are copied by setup. Run
`python3 scripts/render-labs.py` to regenerate this guide and
`python3 scripts/check-labs.py` to check definitions, rendered cards, command syntax
and guide consistency. See [lab-design.md](lab-design.md) for the content contract and source qualifications.

Local checks cannot establish live Ubuntu, Docker or Kubernetes outcomes. Use the
per-lab setup, verify, experiment and recovery checks to collect that evidence.
''')
    return ''.join(parts)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    target = ROOT / 'docs/chaos-labs.md'
    content = render()
    if args.check:
        if not target.exists() or target.read_text(encoding='utf-8') != content:
            parser.exit(1, 'docs/chaos-labs.md is stale; run scripts/render-labs.py\n')
        print('Guide matches all lab definitions.')
    else:
        target.write_text(content, encoding='utf-8', newline='\n')
        print(f'Rendered {len(load_labs())} labs.')
