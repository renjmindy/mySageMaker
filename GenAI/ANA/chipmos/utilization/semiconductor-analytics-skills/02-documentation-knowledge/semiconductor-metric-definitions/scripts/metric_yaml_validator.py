"""
Validator for the metric definition YAML (no PyYAML dependency).

Checks
  * every metric has description, type, formula, owner, version, assumptions
  * owner is not an unfilled template placeholder ([REQUIRED] = FAIL, [OPEN] = WARN)
  * metrics at version > 1 appear in the changelog
  * the cleaning `contract` equals lib/contactor_io.py (statuses and constants)
  * every referenced assumption id exists in the assumptions log
  * optional --recompute: independent recomputation of availability vs the script

Usage:
    python metric_yaml_validator.py
    python metric_yaml_validator.py ../assets/metric_definition.yaml --recompute
"""

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "02-documentation-knowledge/analysis-assumptions-log/scripts"))
sys.path.insert(0, str(ROOT / "03-data-analysis-investigation/site-availability/scripts"))

REQUIRED = ["description", "type", "formula", "owner", "version", "assumptions"]


def _list(text: str, key: str) -> list[str]:
    m = re.search(rf"^\s*{key}:\s*\[([^\]]*)\]", text, re.MULTILINE)
    return [x.strip() for x in m.group(1).split(",") if x.strip()] if m else []


def _int(text: str, key: str):
    m = re.search(rf"^\s*{key}:\s*(-?\d+)", text, re.MULTILINE)
    return int(m.group(1)) if m else None


def metric_blocks(text: str) -> dict[str, str]:
    body = text.split("\nmetrics:", 1)[1] if "\nmetrics:" in text else ""
    parts = re.split(r"\n\s*-\s+name:\s*", body)[1:]
    return {p.splitlines()[0].strip(): p for p in parts}


def validate(text: str) -> tuple[list[str], list[str]]:
    import contactor_io as cio
    import assumptions_tracker as at
    errors, warnings = [], []

    blocks = metric_blocks(text)
    if not blocks:
        errors.append("no metrics found")
    known_ids = {a["id"] for a in at.load()}
    changelog_versions = {int(v) for v in re.findall(r"\{version:\s*(\d+)", text)}

    for name, b in blocks.items():
        for key in REQUIRED:
            if not re.search(rf"^\s*{key}:", b, re.MULTILINE):
                errors.append(f"{name}: missing '{key}'")
        owner = re.search(r"^\s*owner:\s*\"?([^\"\n]*)\"?", b, re.MULTILINE)
        if owner:
            o = owner.group(1).strip()
            if "[REQUIRED]" in o:
                errors.append(f"{name}: owner is an unfilled placeholder")
            elif o == "[OPEN]":
                warnings.append(f"{name}: owner not assigned ([OPEN])")
        ver = _int(b, "version")
        if ver and ver > 1 and ver not in changelog_versions:
            errors.append(f"{name}: version {ver} has no changelog entry")
        for aid in _list(b, "assumptions"):
            if aid not in known_ids:
                errors.append(f"{name}: unknown assumption {aid}")

    contract = text.split("\ncontract:", 1)[1].split("\nsemantic_model:", 1)[0] if "\ncontract:" in text else ""
    if not contract:
        errors.append("no contract section")
    else:
        src = (ROOT / "lib" / "contactor_io.py").read_text(encoding="utf-8")
        m = re.search(r"status:\s*([A-Z_0-9 |]+)\n", src)
        loader_status = {s.strip() for s in m.group(1).split("|")} if m else set()
        valid, dropped = set(_list(contract, "valid_status")), set(_list(contract, "dropped_status"))
        if valid & dropped:
            errors.append(f"contract: statuses both valid and dropped: {sorted(valid & dropped)}")
        if valid | dropped != loader_status:
            errors.append(f"contract statuses {sorted(valid | dropped)} != loader {sorted(loader_status)}")
        for key, actual in (("near_full_min", cio.NEAR_FULL_MIN), ("max_count_gap", cio.MAX_COUNT_GAP),
                            ("max_gap_min", int(cio.DEFAULT_MAX_GAP_MIN))):
            if _int(contract, key) != actual:
                errors.append(f"contract {key}={_int(contract, key)} but loader has {actual}")
        for aid in _list(contract, "assumptions"):
            if aid not in known_ids:
                errors.append(f"contract: unknown assumption {aid}")
    return errors, warnings


def recompute() -> list[str]:
    """Recompute availability from the loader two ways and compare with site_availability.py."""
    import contactor_io as cio
    import site_availability as sa
    lines, problems = [], []
    highs = {}
    for side in cio.SIDES:
        df = cio.load_side(side)
        v = df[df["valid"]]
        high = 1 - (v["n_closed"] * v["weight_min"]).sum() / (256 * v["weight_min"].sum())
        upper = v[["err_01", "n_closed"]].max(axis=1).clip(upper=256)
        low = 1 - (upper * v["weight_min"]).sum() / (256 * v["weight_min"].sum())
        ov = sa.overall(df)
        highs[side] = high
        lines.append(f"{side}: high {high * 100:.2f}% (script {ov['availability_high_pct']}%), low {low * 100:.2f}% (script {ov['availability_low_pct']}%)")
        if abs(high * 100 - ov["availability_high_pct"]) > 0.006 or abs(low * 100 - ov["availability_low_pct"]) > 0.006:
            problems.append(f"{side}: YAML formula and site_availability.py disagree")
    lines.append(f"combined (mean of sides): {sum(highs.values()) / 2 * 100:.2f}%")
    return lines + [f"PROBLEM: {p}" for p in problems]


def main():
    default = HERE.parents[1] / "assets" / "metric_definition.yaml"
    ap = argparse.ArgumentParser(description="Validate metric definition YAML")
    ap.add_argument("path", nargs="?", default=str(default), help="YAML file (default: the bundled definitions)")
    ap.add_argument("--recompute", action="store_true", help="recompute availability independently and compare with the script")
    args = ap.parse_args()

    errors, warnings = validate(Path(args.path).read_text(encoding="utf-8"))
    for w in warnings:
        print("WARN:", w)
    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
    else:
        print("OK - metrics, contract and assumption ids consistent with the loader and the log")
    if args.recompute:
        out = recompute()
        print("\n".join(out))
        if any(l.startswith("PROBLEM") for l in out):
            errors.append("recompute mismatch")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
