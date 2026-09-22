#!/usr/bin/env python3
"""Read a lab without connecting to a VM."""
import argparse
import sys

from lab_content import load_labs, render_card


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lab", help="lab number or list")
    parser.add_argument("action", nargs="?", choices=("question", "solution"), default="question")
    args = parser.parse_args()
    try:
        labs = load_labs()
        if args.lab == "list":
            for lab_id, lab in labs.items():
                print(f'{lab_id}  {lab["title"].split(" — ", 1)[-1]}')
            return
        lab_id = args.lab.zfill(2)
        if lab_id not in labs:
            parser.error(f"unknown lab: {args.lab}")
        print(render_card(lab_id, labs[lab_id], args.action), end="")
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
