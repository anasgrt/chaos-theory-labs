#!/usr/bin/env python3
"""Render a printable companion from the lab definitions (requires ReportLab)."""
import argparse
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Preformatted, Spacer, PageBreak, CondPageBreak, Table, TableStyle

from lab_content import ROOT, load_labs


def render(target, font_dir):
    for name, filename in [('Body', 'DejaVuSans.ttf'), ('Strong', 'DejaVuSans-Bold.ttf'), ('Code', 'DejaVuSansMono.ttf')]:
        pdfmetrics.registerFont(TTFont(name, str(font_dir / filename)))
    width = A4[0] - 88
    body = ParagraphStyle('body', fontName='Body', fontSize=9.3, leading=14, spaceAfter=8)
    small = ParagraphStyle('small', parent=body, fontSize=8, leading=11, spaceAfter=5)
    heading = ParagraphStyle('heading', fontName='Strong', fontSize=17, leading=22, spaceAfter=14, keepWithNext=True, textColor=colors.HexColor('#153e56'))
    subhead = ParagraphStyle('subhead', fontName='Strong', fontSize=10.5, leading=14, spaceBefore=9, spaceAfter=6, keepWithNext=True)
    code_style = ParagraphStyle('code', fontName='Code', fontSize=7.1, leading=10, spaceAfter=10, backColor=colors.HexColor('#f1f4f6'), borderPadding=6)
    story = []

    def clean(text):
        return str(text).replace('—', '-').replace('–', '-').replace('‑', '-').replace('→', ' -> ')

    def p(text, style=body):
        return Paragraph(escape(clean(text)), style)

    def text(value, style=body):
        story.append(p(value, style))

    def table(headers, rows, fractions=None, padding=6):
        widths = [width / len(headers)] * len(headers) if fractions is None else [width * x for x in fractions]
        data = [[p(cell, small) for cell in headers]] + [[p(cell, small) for cell in row] for row in rows]
        block = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
        block.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e3edf2')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEBELOW', (0, 0), (-1, 0), .6, colors.HexColor('#7393a5')),
            ('LINEBELOW', (0, 1), (-1, -1), .3, colors.HexColor('#d2dce2')),
            ('LEFTPADDING', (0, 0), (-1, -1), 7),
            ('RIGHTPADDING', (0, 0), (-1, -1), 7),
            ('TOPPADDING', (0, 0), (-1, -1), padding),
            ('BOTTOMPADDING', (0, 0), (-1, -1), padding),
        ]))
        story.extend([block, Spacer(1, 8)])

    def commands(items, section=None):
        for index, command in enumerate(items, 1):
            # Visual wrapping only; terminal/Markdown retain the exact pasteable command.
            label = [p(section, subhead)] if index == 1 and section else []
            story.extend(label)
            text(f'Step {index}. {command["name"]}', subhead)
            where = p('Run in: ' + command.get('where', 'VM terminal 1'), small)
            where.keepWithNext = True
            story.append(where)
            story.append(Preformatted(clean(command['run'].rstrip()), code_style,
                                      maxLineLength=112, splitChars=' ', newLineChars='    '))
            if command.get('record'):
                text('Record: ' + command['record'], small)

    labs = load_labs()
    text('Chaos labs', heading)
    text('Theory, evidence and controlled experiments', subhead)
    text('Read the relevant theory, predict, measure, explain, and check recovery. Each lab tests one question. The solutions are collected at the end so you can study and run the question without seeing its expected observations.')
    text('Run ./lab.sh provision once. Choose any lab: ./lab.sh NN setup prepares and verifies its fixture in the shared VM. Open ./lab.sh ssh, run the procedure and record your evidence. Compare NN solution. Save results before NN reset removes that lab\'s resources and files.')
    text('Stop if the baseline fails. Confirm the fault actually reached its target. Expected results are not your observations. Use Bash without set -e and preserve the same shell when blocks share variables. Keep a second VM terminal available for recovery.')
    text('All labs use one VM. Each Kubernetes lab owns a separate named kind cluster inside it. No lab sequence is required. Reset finished labs to free resources. ./lab.sh stop halts the whole VM while preserving files. See README.md for capacity.')
    text('Long command lines wrap visually in this print edition. Copy exact commands from docs/chaos-labs.md or the terminal question card. Theory citations use original section numbers in docs/chaos-theory.md.', small)
    entries = [(number, lab['title'].split(' — ', 1)[-1]) for number, lab in labs.items()]
    midpoint = (len(entries) + 1) // 2
    rows = [list(entries[index]) + (list(entries[index + midpoint]) if index + midpoint < len(entries) else ['', ''])
            for index in range(midpoint)]
    table(['Lab', 'Topic', 'Lab', 'Topic'], rows, [.07, .43, .07, .43], padding=3)
    for number, lab in labs.items():
        story.extend([PageBreak()] if number == '00' else [Spacer(1, 18), CondPageBreak(210)])
        task, brief = lab['task'], lab['task']['brief']
        text(lab['title'], heading)
        text(task['question'], subhead)
        text('Before you run: ' + lab['prerequisites'], small)
        text('Theory you need', subhead)
        for paragraph in brief['theory']:
            text(paragraph)
        text('Source: ' + brief['theory_source'], small)
        text('Main lesson to learn in this lab', subhead)
        text(brief['main_lesson'])
        text('Experiment', subhead)
        for point in brief['in_this_lab']:
            text(point)
        text('Before running: ' + task['predict'])
        text('Measurement key', subhead)
        table(['Signal', 'Meaning'], [[r['signal'], r['meaning']] for r in brief['readings']], [.25, .75])
        text('Run the steps', subhead)
        text('After setup, run these commands on the host:', small)
        story.append(Preformatted(f'./lab.sh {number} verify\n./lab.sh ssh', code_style))
        text('This is VM terminal 1. For VM terminal 2, open another host terminal and run ./lab.sh ssh there. '
             'Keep each shell open while steps reuse variables or functions. Run the blocks in order using '
             'Bash without set -e. Stop if the baseline fails.', small)
        commands(lab['commands'])
        text('Recovery check: ' + lab['verify_note'])
        if lab.get('fallback'):
            commands(lab['fallback'], section='Only if normal recovery fails')
        text('Write your answer', subhead)
        text('Use the observations recorded beside each step.', small)
        evidence = task['evidence']
        table(evidence['columns'], [[row] + [''] * (len(evidence['columns']) - 1) for row in evidence['rows']])
        for index, prompt in enumerate(task['answer_with'], 1):
            text(f'{index}. {prompt}')
        text('Apply the same reasoning', subhead)
        text(task['transfer'])
        text(f'Save results before removing this lab\'s resources and files: ./lab.sh {number} reset', small)
    story.append(PageBreak())
    text('Solutions', heading)
    text('Compare after recording your own results. The expected patterns below assume a working baseline and a confirmed injection. Differences require analysis; do not replace observations with the expected answer.')
    for number, lab in labs.items():
        text(lab['title'], subhead)
        for index, (prompt, answer) in enumerate(zip(lab['task']['answer_with'], lab['solution']), 1):
            text(f'{index}. {prompt}', subhead)
            text(answer)
        text('Expected observations by step', subhead)
        text('Use the matching commands in this lab’s question. These are expected patterns, not recorded results.', small)
        for index, command in enumerate(lab['commands'], 1):
            if command.get('expect'):
                text(f'Step {index}. {command["name"]}: {command["expect"]}', small)
        text('Apply the same reasoning: ' + lab['transfer_solution'])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Body', 8)
        canvas.setFillColor(colors.HexColor('#58707d'))
        canvas.drawString(44, 25, 'Chaos labs | Study the mechanism. Record the evidence.')
        canvas.drawRightString(A4[0] - 44, 25, str(doc.page))
        canvas.restoreState()

    target.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(target), pagesize=A4, leftMargin=44, rightMargin=44, topMargin=40, bottomMargin=44,
                                 title='Chaos labs - theory and controlled experiments', author='Chaos Theory Labs')
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f'Rendered {target}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/chaos-labs.pdf')
    parser.add_argument('--font-dir', type=Path, default=Path('/usr/share/fonts/truetype/dejavu'))
    args = parser.parse_args()
    render(args.output, args.font_dir)
