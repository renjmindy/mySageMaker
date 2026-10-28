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


def garbage_tokens(side: str, data_dir, start: str) -> collections.Counter:
    """Tokens in err_02 that fall outside the side's valid range."""
    import glob
    cfg = cio.SIDES[side]
    base = Path(data_dir or cio.DEFAULT_DATA_DIR)
    counter: collections.Counter = collections.Counter()
    for f in sorted(glob.glob(str(base / cfg["pattern"]))):
        raw = pd.read_csv(f, encoding="utf-8-sig", dtype=str, keep_default_na=False)
        raw = raw[raw["Timestamp"] >= start.replace("-", "/")]
        for cnt, lst in zip(raw["err_01"], raw["err_02"]):
            if cnt == str(cio.READ_FAIL_COUNT) or lst.strip() == "N/A":
                continue
            for tok in lst.split(";"):
                tok = tok.strip()
                if tok and not (tok.isdigit() and cfg["lo"] <= int(tok) <= cfg["hi"]):
                    counter[tok] += 1
    return counter


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
        print(f"most common garbage tokens : {garbage_tokens(side, args.data_dir, args.start).most_common(args.top)}")


if __name__ == "__main__":
    main()
