"""
DEFERRED - not part of the current workflow (impact-quantification/status.json). Do not quote its output in
any deliverable until real business parameters exist; the checkers reject such figures while it is deferred.

Capacity and value of recovering closed sites, as an estimate with a range.

  * the data half counts site-equivalents from what is closed NOW (last N days), not the period average -
    a forward decision needs the current loss; the period average is printed as history only
  * the range comes from the recency window (3, 7 and 14 days): low = fewest site-equivalents, high = most
  * NO business parameter has a default: units/hour per site, hours per day, margin per unit, days, repair
    cost, whether the handler is capacity-constrained, the probability the repair holds, repair downtime
    and the sites offline during it must all be supplied (0 is a legitimate explicit value)
  * not capacity-constrained -> no gain (idle capacity absorbs the loss) and no downtime loss; only the repair cost

    gain/h   = site_equivalents x units/h per site
    gross    = gain/h x hours per day x days x margin x P(repair holds)
    downtime = repair_downtime_days x hours per day x sites_offline x units/h per site x margin
    net      = gross - downtime - repair_cost

Usage:
    python cost_impact.py                 # prints the deferral notice (no numbers)
    python cost_impact.py --demo          # ILLUSTRATIVE parameters, clearly labelled
    python cost_impact.py --side front --recover-sites 143 144 159 160 175 176 191 192 \\
        --uph-per-site U --hours-per-day H --margin-per-unit M --days D --repair-cost C \\
        --capacity-constrained yes --p-hold P --repair-downtime-days R --sites-offline-during-repair S
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "03-data-analysis-investigation/chronic-site-detection/scripts"))
import chronic_sites as cs  # noqa: E402
import contactor_io as cio  # noqa: E402
import deferral  # noqa: E402

WINDOWS = (3, 7, 14)
BASE_WINDOW = 7
REQUIRED = ("uph_per_site", "hours_per_day", "margin_per_unit", "days", "repair_cost", "capacity_constrained",
            "p_hold", "repair_downtime_days", "sites_offline_during_repair")


def site_equivalents(side: str, sites: list[int], data_dir=None, near_full_min=cio.NEAR_FULL_MIN,
                     windows=WINDOWS) -> dict:
    """Time-weighted number of the given sites that were closed: whole period (history) and each recent window."""
    df = cio.load_side(side, data_dir, near_full_min=near_full_min)
    mat = cio.closed_matrix(df, side)
    period = cs.closure_share(mat)
    cols = [s for s in sites if s in period.index]
    out = {"period": float(period[cols].sum())}
    for w in sorted(set(windows) | {BASE_WINDOW}):
        out[w] = float(cs.window_share(mat, start=mat.index.max() - pd.Timedelta(days=w))[cols].sum())
    return out


def validate(p: dict) -> list[str]:
    errs = [f"{k} is required (no default)" for k in REQUIRED if p.get(k) is None]
    if errs:
        return errs
    for k in ("uph_per_site", "margin_per_unit", "repair_cost", "repair_downtime_days"):
        if p[k] < 0:
            errs.append(f"{k} must be >= 0")
    if not 0 < p["hours_per_day"] <= 24:
        errs.append("hours_per_day must be in (0, 24]")
    if p["days"] <= 0:
        errs.append("days must be > 0")
    if not 0 <= p["p_hold"] <= 1:
        errs.append("p_hold must be between 0 and 1")
    if not 0 <= p["sites_offline_during_repair"] <= cio.SITES_PER_SIDE:
        errs.append("sites_offline_during_repair must be between 0 and 256")
    if p["capacity_constrained"] not in (True, False):
        errs.append("capacity_constrained must be yes or no")
    return errs


def value(site_eq: float, p: dict) -> dict:
    errs = validate(p)
    if errs:
        raise ValueError("; ".join(errs))
    gain_per_h = site_eq * p["uph_per_site"] if p["capacity_constrained"] else 0.0
    gross = gain_per_h * p["hours_per_day"] * p["days"] * p["margin_per_unit"] * p["p_hold"]
    downtime = (p["repair_downtime_days"] * p["hours_per_day"] * p["sites_offline_during_repair"] * p["uph_per_site"] * p["margin_per_unit"]
                if p["capacity_constrained"] else 0.0)
    return {"site_equivalents": site_eq, "gain_units_per_hour": gain_per_h, "gross_value": gross,
            "downtime_loss": downtime, "repair_cost": p["repair_cost"], "net_value": gross - downtime - p["repair_cost"]}


def scenarios(se: dict, p: dict) -> dict:
    """low / mid / high from the recency windows (history is reported separately, never used)."""
    vals = {w: se[w] for w in WINDOWS}
    pick = {"low": min(vals.values()), "mid": se[BASE_WINDOW], "high": max(vals.values())}
    return {k: value(v, p) for k, v in pick.items()}


def main():
    ap = argparse.ArgumentParser(description="Capacity and value of recovering closed sites (DEFERRED)")
    ap.add_argument("--demo", action="store_true", help="ILLUSTRATIVE parameters, clearly labelled")
    ap.add_argument("--side", choices=["front", "rear"], default="front")
    ap.add_argument("--recover-sites", type=int, nargs="*")
    ap.add_argument("--uph-per-site", type=float)
    ap.add_argument("--hours-per-day", type=float)
    ap.add_argument("--margin-per-unit", type=float)
    ap.add_argument("--days", type=float)
    ap.add_argument("--repair-cost", type=float)
    ap.add_argument("--capacity-constrained", choices=["yes", "no"])
    ap.add_argument("--p-hold", type=float, help="probability the repair holds (0-1)")
    ap.add_argument("--repair-downtime-days", type=float)
    ap.add_argument("--sites-offline-during-repair", type=float)
    ap.add_argument("--scenario", choices=["low", "mid", "high", "all"], default="all")
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN)
    ap.add_argument("--data-dir", default=None)
    args = ap.parse_args()

    supplied = [getattr(args, k) for k in REQUIRED] + [args.recover_sites]
    if not args.demo and all(v is None for v in supplied):
        print("impact-quantification is DEFERRED (status.json): no real business parameters exist yet.")
        print("Nothing is computed. Use --demo for a labelled illustration, or supply every business parameter.")
        return

    if args.demo:
        print("ILLUSTRATIVE parameters - NOT real data. Do not quote these figures anywhere.")
        args.recover_sites = [143, 144, 159, 160, 175, 176, 191, 192]
        args.side = "front"
        demo = dict(uph_per_site=20.0, hours_per_day=20.0, margin_per_unit=0.05, days=30.0, repair_cost=3000.0,
                    capacity_constrained="yes", p_hold=0.8, repair_downtime_days=0.5, sites_offline_during_repair=8.0)
        for k, v in demo.items():
            setattr(args, k, v)
    elif deferral.is_deferred():
        print("WARNING: impact-quantification is DEFERRED - do not quote this output in any deliverable.")
    if not args.recover_sites:
        ap.error("--recover-sites is required")

    p = {k: getattr(args, k) for k in REQUIRED}
    p["capacity_constrained"] = {"yes": True, "no": False, None: None}[p["capacity_constrained"]]
    errs = validate(p)
    if errs:
        ap.error("; ".join(errs))

    se = site_equivalents(args.side, args.recover_sites, args.data_dir, args.near_full_min)
    print(f"site-equivalents (of {len(args.recover_sites)} sites) on {args.side}: "
          + ", ".join(f"last {w} days {se[w]:.2f}" for w in WINDOWS)
          + f" | whole-period average {se['period']:.2f} (history only, not used)")
    res = scenarios(se, p)
    for k in (["low", "mid", "high"] if args.scenario == "all" else [args.scenario]):
        r = res[k]
        print(f"  {k:4s}: site-equivalents {r['site_equivalents']:.2f}  gain {r['gain_units_per_hour']:.1f} units/h  "
              f"gross {r['gross_value']:.0f}  downtime {r['downtime_loss']:.0f}  repair {r['repair_cost']:.0f}  NET {r['net_value']:.0f}")
    if not p["capacity_constrained"]:
        print("  not capacity-constrained: no gain counted; only the repair cost remains")


if __name__ == "__main__":
    main()
