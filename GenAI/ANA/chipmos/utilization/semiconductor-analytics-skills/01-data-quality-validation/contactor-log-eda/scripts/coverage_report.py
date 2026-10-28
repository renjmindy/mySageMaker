"""
Closed-site distribution and site coverage per side.

Usage:
    python coverage_report.py
    python coverage_report.py --side rear
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import contactor_io as cio  # noqa: E402


def distribution(df) -> dict:
    v = df[df["valid"]]
    n = v["n_closed"].to_numpy()
    ever = set()
    for s in v["sites"]:
        ever.update(s)
    return {
        "valid_samples": len(v),
        "n_closed min": int(n.min()),
        "n_closed p50": float(np.percentile(n, 50)),
        "n_closed p90": float(np.percentile(n, 90)),
        "n_closed max": int(n.max()),
        "zero-closed samples %": round(float((n == 0).mean() * 100), 1),
        "distinct sites ever closed": len(ever),
        "time-weighted availability %": round(cio.weighted_availability(df) * 100, 2),
    }


def main():
    ap = argparse.ArgumentParser(description="Closed-site distribution per side")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--side", choices=["front", "rear", "both"], default="both")
    ap.add_argument("--start", default=cio.DEFAULT_START)
    args = ap.parse_args()

    for side in (cio.SIDES if args.side == "both" else [args.side]):
        print(f"\n=== {side.upper()} distribution ===")
        for k, v in distribution(cio.load_side(side, args.data_dir, args.start)).items():
            print(f"{k:32s} {v}")


if __name__ == "__main__":
    main()
