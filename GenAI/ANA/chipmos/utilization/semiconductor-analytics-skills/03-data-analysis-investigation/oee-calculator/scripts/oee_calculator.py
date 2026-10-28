"""
OEE = Availability x Performance x Quality, with an honest completeness flag.

Usage:
    python oee_calculator.py --demo                       # doc example -> 77.1%
    python oee_calculator.py --run-min 400 --planned-min 480 --output 380 --good 370 --ideal-cycle-min 1.0
    python oee_calculator.py --site-availability 0.90     # partial: capacity factor only
"""

import argparse


def oee(run_min=None, planned_min=None, output=None, good=None, ideal_cycle_min=None, site_availability=None):
    res = {"availability": None, "performance": None, "quality": None, "site_availability": site_availability}
    if run_min is not None and planned_min:
        res["availability"] = run_min / planned_min
    if None not in (output, ideal_cycle_min, run_min) and run_min:
        res["performance"] = output * ideal_cycle_min / run_min
    if good is not None and output:
        res["quality"] = good / output
    parts = [res["availability"], res["performance"], res["quality"]]
    res["complete"] = all(p is not None for p in parts)
    known = [p for p in parts if p is not None]
    prod = 1.0
    for p in known:
        prod *= p
    res["oee"] = prod if res["complete"] else None  # OEE stays blocked until A, P and Q are all measured
    res["missing"] = [n for n, p in zip(("availability", "performance", "quality"), parts) if p is None]
    return res


def show(res):
    pct = lambda x: "n/a" if x is None else f"{x * 100:.1f}%"
    print(f"Availability (A): {pct(res['availability'])}")
    print(f"Performance  (P): {pct(res['performance'])}")
    print(f"Quality      (Q): {pct(res['quality'])}")
    if res["site_availability"] is not None:
        print(f"Site availability (capacity factor, not time): {pct(res['site_availability'])}")
    if res["complete"]:
        print(f"OEE: {pct(res['oee'])}")
    else:
        print(f"OEE: BLOCKED - missing {', '.join(res['missing'])} (needs run-state, output, good-unit and cycle-time data)")


def main():
    ap = argparse.ArgumentParser(description="OEE calculator")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--run-min", type=float)
    ap.add_argument("--planned-min", type=float)
    ap.add_argument("--output", type=float)
    ap.add_argument("--good", type=float)
    ap.add_argument("--ideal-cycle-min", type=float)
    ap.add_argument("--site-availability", type=float)
    args = ap.parse_args()
    if args.demo or not any(v is not None for v in vars(args).values() if v is not False):
        # ideal cycle chosen so that P = 95.0% as in the doc example
        show(oee(400, 480, 380, 370, 400 * 0.95 / 380))
        return
    show(oee(args.run_min, args.planned_min, args.output, args.good, args.ideal_cycle_min, args.site_availability))


if __name__ == "__main__":
    main()
