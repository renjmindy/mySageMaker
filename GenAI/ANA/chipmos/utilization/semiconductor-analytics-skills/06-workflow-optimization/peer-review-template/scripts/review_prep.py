"""
Generate the author's preparation block of a peer review from the project's own files and the data.

The block lists the claims a reviewer must reproduce (headline, lower bound, range, closed now, per side), the
deliverable files where each appears, the author's recomputation without the loader (independent_recompute.py),
the rules the results depend on that are not confirmed, the waivers in effect and the deliverables under review.
It sits between the generated markers of the review record; `--check` fails if the record is out of date, and
`--write` regenerates it (and refreshes the author-value column of the reviewer's reproduction table).

Usage:
    python review_prep.py            # print the block
    python review_prep.py --write
    python review_prep.py --check
"""

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
BASE = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "06-workflow-optimization/context-packager/scripts"))
import context_bundler as cb  # noqa: E402
import independent_recompute as ir  # noqa: E402

REVIEW = BASE / "assets" / "peer_review_sep_oct_2026.md"
START, END = "<!-- generated:start -->", "<!-- generated:end -->"
RUN = {"availability": "python 03-data-analysis-investigation/site-availability/scripts/site_availability.py",
       "closed": "python 03-data-analysis-investigation/chronic-site-detection/scripts/chronic_sites.py --side {side}"}


def claims(fresh: dict) -> list[dict]:
    out = []
    for key, label, fmt in (("availability", "site availability (%)", "{:.2f}"), ("lower_bound", "lower bound (%)", "{:.2f}")):
        for side, v in fresh["sides"].items():
            out.append({"claim": f"{side} {label}", "value": fmt.format(v[key]), "needles": [fmt.format(v[key])], "command": RUN["availability"]})
    for side, v in fresh["sides"].items():
        out.append({"claim": f"{side} 95% range (%)", "value": f"{v['ci_low']:.2f}-{v['ci_high']:.2f}",
                    "needles": [f"{v['ci_low']:.2f}", f"{v['ci_high']:.2f}"], "command": RUN["availability"]})
    for side, v in fresh["sides"].items():
        n = v["closed_now"]
        out.append({"claim": f"{side} positions closed now (of 256)", "value": str(n), "needles": [f"{n} of 256", f"{n}/256"],
                    "command": RUN["closed"].format(side=side), "any": True})
    for i, c in enumerate(out, 1):
        c["id"] = f"C{i}"
    return out


def deliverables(root: Path = ROOT) -> list[str]:
    """Every filled Sep-Oct deliverable in the skills' assets, except the review records themselves."""
    skip = ("peer_review_", "review_response_")
    return sorted(p.relative_to(root).as_posix() for p in root.glob("0*/*/assets/*_sep_oct_2026.md") if not p.name.startswith(skip))


def appears_in(c: dict, files: list[str], root: Path = ROOT) -> list[str]:
    hits = []
    for f in files:
        t = (root / f).read_text(encoding="utf-8", errors="ignore")
        if (any(n in t for n in c["needles"]) if c.get("any") else all(n in t for n in c["needles"])):
            hits.append(Path(f).name)
    return hits


def generate(fresh: dict, indep: dict, root: Path = ROOT) -> str:
    files = deliverables(root)
    cl = claims(fresh)
    lines = ["### Claims to reproduce", "| id | claim | author value | where it appears | command |", "|---|---|---|---|---|"]
    for c in cl:
        lines.append(f"| {c['id']} | {c['claim']} | {c['value']} | {', '.join(appears_in(c, files, root)) or '-'} | `{c['command']}` |")
    lines += ["", "### Author's recomputation without the loader (`scripts/independent_recompute.py`)",
              "| side | availability (%) | lower bound (%) | valid readings | difference from the loader-based figure (points) |", "|---|---|---|---|---|"]
    for side, v in indep.items():
        lines.append(f"| {side} | {v['high']:.4f} | {v['low']:.4f} | {v['valid']} | {round(v['high'], 2) - fresh['sides'][side]['availability']:+.2f} |")
    lines += ["", "### Rules the results depend on that the process owner has not confirmed"]
    lines += [f"- {a['id']} ({a['status']}): {a['statement'][:110]}" for a in cb.at.load() if a["status"] != "CONFIRMED"]
    lines += ["", "### Waivers in effect", "| check | owner | expires |", "|---|---|---|"]
    lines += [f"| {w['check']} | {w['owner']} | {w['expires']} |" for w in json.loads(cb.WAIVERS.read_text(encoding="utf-8"))]
    lines += ["", "### Deliverables under review"] + [f"- `{f}`" for f in files]
    return "\n".join(lines)


def block_of(text: str) -> str:
    m = re.search(re.escape(START) + r"\n(.*?)\n" + re.escape(END), text, re.DOTALL)
    return m.group(1) if m else ""


def current(data_dir=None) -> tuple[str, list[dict]]:
    fresh = cb.fresh_state(data_dir)
    return generate(fresh, ir.recompute(data_dir)), claims(fresh)


def write(text: str, block: str, cl: list[dict]) -> str:
    """Regenerate the block, then refresh the claim and author-value cells of the reviewer's table (outside the block)."""
    text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: f"{START}\n{block}\n{END}", text, flags=re.DOTALL)
    head, rest = text.split(END, 1)
    by_id, out = {c["id"]: c for c in cl}, []
    for line in rest.splitlines():
        m = re.match(r"\| (C\d+) \|", line)
        if m and m.group(1) in by_id:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            cells += [""] * (5 - len(cells))
            c = by_id[m.group(1)]
            line = f"| {c['id']} | {c['claim']}: {c['value']} | {cells[2]} | {cells[3]} | {cells[4]} |"
        out.append(line)
    return head + END + "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Generate the author's preparation block of the peer review")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    block, cl = current()
    text = REVIEW.read_text(encoding="utf-8") if REVIEW.exists() else ""
    if args.write:
        REVIEW.write_text(write(text, block, cl), encoding="utf-8")
        print(f"wrote {REVIEW}")
    elif args.check:
        if block_of(text) != block:
            print("STALE - run: python review_prep.py --write")
            sys.exit(1)
        print("OK - the author's preparation is current")
    else:
        print(block)


if __name__ == "__main__":
    main()
