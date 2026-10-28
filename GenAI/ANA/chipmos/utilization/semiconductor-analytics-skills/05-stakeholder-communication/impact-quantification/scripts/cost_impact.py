"""
DEFERRED - not part of the current workflow; do not use until real business parameters exist.

Capacity and value of recovering closed sites.

Business parameters are NEVER defaulted - supply them (or use --demo, which uses
clearly labelled illustrative numbers).

Usage:
    python cost_impact.py --side front --recover-sites 143 144 159 160 175 176 191 192 \
        --uph-per-site 20 --hours-per-day 24 --margin-per-unit 0.05 --days 30 --repair-cost 3000
    python cost_impact.py --demo
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import contactor_io as cio  # noqa: E402


def site_equivalents(side: str, sites: list[int], data_dir=None, near_full_min=cio.NEAR_FULL_MIN) -> float:
    """Time-weighted average number of the given sites that were closed."""
    df = cio.load_side(side, data_dir, near_full_min=near_full_min)
    mat = cio.closed_matrix(df, side)
    w = mat["weight_min"]
    cols = [s for s in sites if s in mat.columns]
    return float((mat[cols].astype(float).mul(w, axis=0).sum() / w.sum()).sum())


def value(site_eq, uph_per_site, hours_per_day, margin_per_unit, days, repair_cost):
    units_per_hour = site_eq * uph_per_site
    units = units_per_hour * hours_per_day * days
    gross = units * margin_per_unit
    return {"site_equivalents": round(site_eq, 2), "units_per_hour": round(units_per_hour, 1),
            "units_over_period": round(units), "gross_value": round(gross),
            "net_value": round(gross - repair_cost)}


def main():
    ap = argparse.ArgumentParser(description="Capacity and cost impact of recovered sites")
    ap.add_argument("--side", choices=["front", "rear"], default="front")
    ap.add_argument("--recover-sites", type=int, nargs="*")
    ap.add_argument("--uph-per-site", type=float)
    ap.add_argument("--hours-per-day", type=float, default=24.0)
    ap.add_argument("--margin-per-unit", type=float)
    ap.add_argument("--days", type=float, default=30.0)
    ap.add_argument("--repair-cost", type=float, default=0.0)
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN, help="err_01 >= N (<256) is a read failure; 0 disables")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()

    if args.demo or not (args.recover_sites or args.uph_per_site or args.margin_per_unit):
        print("ILLUSTRATIVE parameters (not real): uph/site=20, margin/unit=0.05, 30 days, repair=3000")
        args.recover_sites = [143, 144, 159, 160, 175, 176, 191, 192]
        args.uph_per_site, args.margin_per_unit, args.repair_cost = 20.0, 0.05, 3000.0
    if not args.recover_sites:
        ap.error("--recover-sites required")
    se = site_equivalents(args.side, args.recover_sites, args.data_dir, args.near_full_min)
    print(f"site-equivalents recovered on {args.side}: {se:.2f} of 256 ({se / 256 * 100:.2f} availability points)")
    if args.uph_per_site is None or args.margin_per_unit is None:
        print("units/hour per site and margin per unit not supplied - capacity/value not computed")
        return
    for k, v in value(se, args.uph_per_site, args.hours_per_day, args.margin_per_unit, args.days, args.repair_cost).items():
        print(f"{k:20s} {v}")


if __name__ == "__main__":
    main()
