"""Shared lab loading, validation and terminal rendering."""
from pathlib import Path
import re

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]


class Loader(yaml.SafeLoader):
    pass


Loader.add_constructor("!unsafe", lambda loader, node: loader.construct_scalar(node))


def lab_paths():
    paths = {}
    for path in sorted((ROOT / "labs").glob("[0-9][0-9]-*/lab.yml")):
        lab_id = path.parent.name[:2]
        if lab_id in paths:
            raise ValueError(f"Duplicate lab ID: {lab_id}")
        paths[lab_id] = path
    if not paths:
        raise ValueError("No lab definitions found")
    return paths


def fixture_path(lab_id, filename):
    if not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", filename):
        raise ValueError("Fixture names must be plain filenames within the lab's files directory")
    return lab_paths()[lab_id].parent / "files" / filename


def load_labs():
    labs = {}
    for lab_id, path in lab_paths().items():
        lab = yaml.load(path.read_text(encoding="utf-8"), Loader=Loader)
        validate(lab, lab_id)
        labs[lab_id] = lab
    return labs


def validate(lab, lab_id):
    def require(condition, message):
        if not condition:
            raise ValueError(f"Lab {lab_id}: {message}")

    for field in ("title", "solution", "transfer_solution", "verify_note", "prerequisites"):
        require(isinstance(lab.get(field), str) and lab[field].strip(), f"missing {field}")
    task = lab.get("task", {})
    for field in ("question", "predict", "answer_with", "transfer"):
        require(isinstance(task.get(field), str) and task[field].strip(), f"missing task.{field}")
    brief = task.get("brief", {})
    require(bool(brief.get("theory_source")), "missing theory source")
    for field in ("theory", "in_this_lab"):
        require(isinstance(brief.get(field), list) and bool(brief[field]), f"missing brief.{field}")
        require(all(isinstance(p, str) and p.strip() for p in brief[field]), f"empty brief.{field} paragraph")
    readings = brief.get("readings", [])
    require(bool(readings), "missing measurement explanations")
    for reading in readings:
        require(bool(reading.get("signal")) and bool(reading.get("meaning")), "incomplete measurement explanation")
    evidence = task.get("evidence", {})
    require(bool(evidence.get("columns")) and bool(evidence.get("rows")), "missing evidence table")
    for group in ("commands", "setup", "verify", "reset", "fallback"):
        require(isinstance(lab.get(group, []), list), f"{group} must be a list")
        for step in lab.get(group, []):
            key = "run" if group in ("commands", "fallback") else "command"
            require(bool(step.get("name")) and bool(step.get(key)), f"incomplete {group} step")
    require(bool(lab.get("commands")), "missing core procedure")
    require(isinstance(lab.get("files", []), list), "files must be a list")
    for name in lab.get("files", []):
        require(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name),
                "fixture names must be plain filenames within this lab's files directory")
    require("concept" not in lab and "mechanism" not in lab, "theory must have one source")


def render_card(lab_id, lab, action):
    env = Environment(
        loader=FileSystemLoader(ROOT / "ansible/templates"),
        undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    template = "task.txt.j2" if action == "question" else "solution.txt.j2"
    return env.get_template(template).render(lab_id=lab_id, selected_lab=lab)
