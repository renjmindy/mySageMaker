"""
Reproduction check for an analysis document.

Runs every command in the document's "## Reproduce" bash blocks (from the repo root)
and verifies that each number listed in the `<!-- check-numbers: a | b | c -->`
comment appears in the combined output. Exit code 1 if a command fails or a number
is missing - i.e. the document no longer matches what the code produces.

Usage:
    python doc_numbers_check.py
    python doc_numbers_check.py ../assets/handler_utilization_analysis_sep_oct_2026.md
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
DEFAULT_DOC = HERE.parents[1] / "assets" / "handler_utilization_analysis_sep_oct_2026.md"


def extract(text: str) -> tuple[list[str], list[str]]:
    m = re.search(r"<!--\s*check-numbers:\s*(.*?)\s*-->", text, re.DOTALL)
    numbers = [n.strip() for n in m.group(1).split("|") if n.strip()] if m else []
    repro = text.split("## Reproduce", 1)[1] if "## Reproduce" in text else ""
    cmds = []
    for block in re.findall(r"```bash\n(.*?)```", repro, re.DOTALL):
        cmds += [l.strip() for l in block.splitlines() if l.strip() and not l.strip().startswith("#")]
    return cmds, numbers


def main():
    ap = argparse.ArgumentParser(description="Re-run an analysis document's commands and check its numbers")
    ap.add_argument("doc", nargs="?", default=str(DEFAULT_DOC))
    args = ap.parse_args()

    cmds, numbers = extract(Path(args.doc).read_text(encoding="utf-8"))
    if not cmds or not numbers:
        sys.exit("FAIL: document needs a '## Reproduce' bash block and a check-numbers comment")

    env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "")}  # clean environment
    output, failed = "", []
    for c in cmds:
        run = re.sub(r"^python3? ", f"{sys.executable} -I ", c)
        p = subprocess.run(run, shell=True, cwd=ROOT, capture_output=True, text=True, env=env, timeout=300)
        output += p.stdout + p.stderr
        status = "ok" if p.returncode == 0 else f"EXIT {p.returncode}"
        print(f"[{status:7s}] {c}")
        if p.returncode != 0:
            failed.append(c)

    missing = [n for n in numbers if n not in output]
    for n in numbers:
        print(f"  {'found  ' if n not in missing else 'MISSING'} {n}")
    print(f"\n{len(cmds)} commands, {len(numbers)} numbers: {len(failed)} command failure(s), {len(missing)} missing")
    sys.exit(1 if failed or missing else 0)


if __name__ == "__main__":
    main()
