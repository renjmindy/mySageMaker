"""
Site-ID sanity check: out-of-range IDs, duplicates and the most common garbage tokens.

Front sites must be 1-256, rear 257-512. Anything else is OCR noise.

Usage:
    python site_id_validator.py
    python site_id_validator.py --side rear --top 15
"""

import argparse
import collections
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import contactor_io as cio  # noqa: E402


def garbage_tokens(side: str, data_dir, start: str, near_full_min: int = cio.NEAR_FULL_MIN) -> tuple[collections.Counter, int]:
    """Out-of-range tokens in err_02, counted only from rows the loader KEEPS.

    Returns (tokens in kept rows, number of tokens in dropped read-failure rows that were ignored).
    """
    import glob
    cfg = cio.SIDES[side]
    base = Path(data_dir or cio.DEFAULT_DATA_DIR)
    counter: collections.Counter = collections.Counter()
    ignored = 0
    for f in sorted(glob.glob(str(base / cfg["pattern"]))):
        raw = pd.read_csv(f, encoding="utf-8-sig", dtype=str, keep_default_na=False)
        raw = raw[raw["Timestamp"] >= start.replace("-", "/")]
        for cnt, lst in zip(raw["err_01"], raw["err_02"]):
            if lst.strip() == "N/A":
                continue
            dropped = int(cnt) == cio.READ_FAIL_COUNT or (near_full_min and int(cnt) >= near_full_min)
            for tok in lst.split(";"):
                tok = tok.strip()
                if tok and not (tok.isdigit() and cfg["lo"] <= int(tok) <= cfg["hi"]):
                    if dropped:
                        ignored += 1
                    else:
                        counter[tok] += 1
    return counter, ignored


def by_month(ok) -> dict:
    """Per month: share of readable rows with an out-of-range ID, and share of all listed numbers that are out of range."""
    out = {}
    for m, g in ok.groupby(ok["timestamp"].dt.strftime("%Y-%m")):
        listed = int(g["n_closed"].sum() + g["n_oob"].sum() + g["n_dup"].sum())
        out[m] = {"rows_pct": round(float((g["n_oob"] > 0).mean() * 100), 1),
                  "numbers_pct": round(float(g["n_oob"].sum() / listed * 100), 1) if listed else 0.0}
    return out


def main():
    ap = argparse.ArgumentParser(description="Validate site IDs in contactor logs")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--side", choices=["front", "rear", "both"], default="both")
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()

    for side in (cio.SIDES if args.side == "both" else [args.side]):
        df = cio.load_side(side, args.data_dir, args.start)
        ok = df[df["status"] == "OK"]
        print(f"\n=== {side.upper()} site-ID validation ({len(ok)} readable rows) ===")
        print(f"rows with out-of-range IDs : {(ok['n_oob'] > 0).sum()} ({(ok['n_oob'] > 0).mean() * 100:.1f}%)")
        print(f"total out-of-range IDs     : {int(ok['n_oob'].sum())}")
        print(f"rows with duplicate IDs    : {(ok['n_dup'] > 0).sum()} ({(ok['n_dup'] > 0).mean() * 100:.1f}%)")
        for m, s in by_month(ok).items():
            print(f"out-of-range IDs {m}: {s['rows_pct']}% of readable rows, {s['numbers_pct']}% of all listed numbers")
        tokens, ignored = garbage_tokens(side, args.data_dir, args.start)
        print(f"most common garbage tokens (kept rows only): {tokens.most_common(args.top)}")
        print(f"garbage tokens ignored because their row is a dropped read failure: {ignored}")
        print("note: why tokens appear (OCR split/merge) is NOT established - compare against screenshots")


if __name__ == "__main__":
    main()
