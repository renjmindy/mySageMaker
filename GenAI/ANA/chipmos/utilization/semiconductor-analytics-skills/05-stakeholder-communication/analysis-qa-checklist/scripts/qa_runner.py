"""
Automated QA checks for the contactor utilization analysis.

Exit code 1 if any check FAILs.

Usage:
    python qa_runner.py
    python qa_runner.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import contactor_io as cio  # noqa: E402


def run(data_dir, start, near_full_min):
    results = []
    add = lambda name, status, detail: results.append((name, status, detail))
    base = {s: cio.load_side(s, data_dir, start, near_full_min=0) for s in cio.SIDES}  # old 256-only rule, for reference
    used = {s: cio.load_side(s, data_dir, start, near_full_min=near_full_min) for s in cio.SIDES}

    for side, df in used.items():
        v = df[df["valid"]]
        add(f"{side}: scope starts {start}", "PASS" if df["timestamp"].min() >= __import__("pandas").Timestamp(start) else "FAIL",
            f"first sample {df['timestamp'].min()}")
        fail = 1 - len(v) / len(df)
        add(f"{side}: read-failure rate", "PASS" if fail < 0.03 else "WARN" if fail < 0.10 else "FAIL", f"{fail * 100:.2f}%")
        add(f"{side}: closed within 0-256", "PASS" if v["n_closed"].between(0, 256).all() else "FAIL", f"max {v['n_closed'].max()}")
        ids_ok = all(cio.SIDES[side]["lo"] <= s <= cio.SIDES[side]["hi"] for ids in v["sites"] for s in ids)
        add(f"{side}: IDs inside side range", "PASS" if ids_ok else "FAIL", "")
        near = int(v["err_01"].between(cio.NEAR_FULL_MIN, 255).sum())
        add(f"{side}: err_01 252-255 rows kept as valid", "PASS" if near == 0 else "FAIL", f"{near} rows (A8 confirmed read failure)")
        lo_hi_gap = (v["err_01"].clip(upper=256).sub(v["n_closed"]).clip(lower=0) * v["weight_min"]).sum() / v["weight_min"].sum() / 256 * 100
        add(f"{side}: count-vs-list gap (availability pts)", "PASS" if lo_hi_gap < 1 else "WARN", f"{lo_hi_gap:.2f} pts between high and low bound")
        unw = (1 - v["n_closed"].mean() / 256) * 100
        wtd = cio.weighted_availability(df) * 100
        add(f"{side}: weighted vs unweighted", "PASS" if abs(unw - wtd) < 2 else "WARN", f"{wtd:.2f}% vs {unw:.2f}%")
        days = df.groupby(df["timestamp"].dt.date).size()
        low = int((days < 0.75 * 360).sum())
        add(f"{side}: days with < 75% coverage", "PASS" if low <= 1 else "WARN", f"{low} days (last day may be partial)")
        b = cio.weighted_availability(base[side]) * 100
        add(f"{side}: effect of 252-255 rule (info)", "PASS", f"{b:.2f}% (256-only) -> {wtd:.2f}% (confirmed rule)")
    return results


def main():
    ap = argparse.ArgumentParser(description="Automated QA for contactor analysis")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN, help="err_01 >= N (<256) is a read failure; 0 disables")
    args = ap.parse_args()
    res = run(args.data_dir, args.start, args.near_full_min)
    for name, status, detail in res:
        print(f"[{status:4s}] {name:52s} {detail}")
    fails = sum(1 for _, s, _ in res if s == "FAIL")
    warns = sum(1 for _, s, _ in res if s == "WARN")
    print(f"\n{len(res)} checks: {fails} FAIL, {warns} WARN")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
