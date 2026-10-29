"""
Recompute site availability straight from the raw CSV files, without the shared loader and without pandas.

A reviewer runs this to reproduce the headline without trusting `lib/contactor_io.py`. It re-implements the
documented cleaning rules from the assumptions log on purpose (so a mistake in the loader does not carry over):

  * read failure: err_01 == 256, or 252-255 (A8), or N/A with a count above 0 (A9), or count - listed positions > 50 (A15)
  * N/A with count 0 is a valid reading with nothing closed; listed IDs outside the side's range and duplicates are ignored (A17)
  * each valid reading counts for the minutes until the next row (any row, dropped or not), capped at 15 (A18);
    the last row gets the median gap
  * availability = 1 - sum(closed x minutes) / (256 x sum(minutes)); the lower bound uses max(err_01, listed) as closed

Usage:
    python independent_recompute.py
    python independent_recompute.py --data-dir ../../../../dat --start 2026-09-01
"""

import argparse
import csv
import datetime as dt
import glob
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SIDES = {"front": ("contactor_2026*.csv", 1, 256), "rear": ("contactor_rear_2026*.csv", 257, 512)}
READ_FAIL, NEAR_FULL, MAX_GAP_COUNT, CAP_MIN, SITES = 256, 252, 50, 15.0, 256


def recompute_side(side: str, data_dir, start: str = "2026-09-01") -> dict:
    pattern, lo, hi = SIDES[side]
    rows = []
    for f in sorted(glob.glob(str(Path(data_dir) / pattern))):
        with open(f, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                rows.append((dt.datetime.strptime(r["Timestamp"], "%Y/%m/%d %H:%M"), int(r["err_01"]), r["err_02"].strip()))
    first = dt.datetime.strptime(start, "%Y-%m-%d")
    rows = sorted((r for r in rows if r[0] >= first), key=lambda r: r[0])  # stable: first of equal timestamps wins
    uniq = []
    for r in rows:
        if not uniq or uniq[-1][0] != r[0]:
            uniq.append(r)
    gaps = [(b[0] - a[0]).total_seconds() / 60 for a, b in zip(uniq, uniq[1:])]
    typical = statistics.median(gaps) if gaps else 4.0
    weights = [min(g, CAP_MIN) for g in gaps] + [min(typical, CAP_MIN)]
    num_high = num_low = den = 0.0
    valid = 0
    for (ts, cnt, lst), w in zip(uniq, weights):
        if cnt == READ_FAIL:
            continue
        if lst == "N/A":
            if cnt != 0:
                continue
            closed = 0
        elif cnt >= NEAR_FULL:
            continue
        else:
            ids = {int(t) for t in lst.split(";") if t.strip().isdigit() and lo <= int(t) <= hi}
            if cnt - len(ids) > MAX_GAP_COUNT:
                continue
            closed = len(ids)
        valid += 1
        den += w
        num_high += closed * w
        num_low += min(max(cnt, closed), SITES) * w
    return {"high": (1 - num_high / (SITES * den)) * 100, "low": (1 - num_low / (SITES * den)) * 100, "valid": valid}


def recompute(data_dir=None, start: str = "2026-09-01") -> dict:
    folder = Path(data_dir) if data_dir else ROOT.parent / "dat"
    return {s: recompute_side(s, folder, start) for s in SIDES}


def main():
    ap = argparse.ArgumentParser(description="Independent recompute of site availability (no loader)")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--start", default="2026-09-01")
    args = ap.parse_args()
    res = recompute(args.data_dir, args.start)
    for side, v in res.items():
        print(f"{side}: availability {v['high']:.4f}%  lower bound {v['low']:.4f}%  valid readings {v['valid']}")
    print(f"combined (mean of sides): {sum(v['high'] for v in res.values()) / 2:.4f}%")


if __name__ == "__main__":
    main()
