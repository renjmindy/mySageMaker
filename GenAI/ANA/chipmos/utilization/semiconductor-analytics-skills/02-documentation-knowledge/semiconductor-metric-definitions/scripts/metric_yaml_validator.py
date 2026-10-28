"""
Lightweight validator for metric definition YAML (no PyYAML dependency).

Checks that every `- name:` metric block has description, type, formula, owner
and version.

Usage:
    python metric_yaml_validator.py ../assets/metric_definition.yaml
"""

import argparse
import re
import sys
from pathlib import Path

REQUIRED = ["description", "type", "formula", "owner", "version"]


def validate(text: str) -> list[str]:
    errors = []
    after = text.split("\nmetrics:", 1)
    if len(after) < 2:
        return ["no `metrics:` section"]
    blocks = re.split(r"\n\s*-\s+name:\s*", after[1])[1:]
    if not blocks:
        errors.append("no metrics found")
    for b in blocks:
        name = b.splitlines()[0].strip()
        for key in REQUIRED:
            if not re.search(rf"^\s*{key}:", b, re.MULTILINE):
                errors.append(f"{name}: missing '{key}'")
    return errors


def main():
    ap = argparse.ArgumentParser(description="Validate metric definition YAML")
    default = Path(__file__).resolve().parents[1] / "assets" / "metric_definition.yaml"
    ap.add_argument("path", nargs="?", default=str(default), help="YAML file (default: the bundled template)")
    args = ap.parse_args()
    errs = validate(open(args.path, encoding="utf-8").read())
    if errs:
        print("FAIL")
        for e in errs:
            print(" -", e)
        sys.exit(1)
    print("OK - all metrics have required keys")


if __name__ == "__main__":
    main()
