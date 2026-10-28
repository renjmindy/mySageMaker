"""
OEE = Availability x Performance x Quality, with validation and an honest BLOCKED state.

Inputs (all minutes / counts; a zero is a value, only None means "not supplied"):
  run_min           minutes the handler actually ran
  planned_min       planned load time in minutes (> 0): total time minus planned downtime
  output            units tested (>= 0)
  good              good units (0 <= good <= output)
  ideal_cycle_min   ideal minutes per unit at the HANDLER level with ALL sites open (> 0)
  site_availability optional share of sites open (0-1). It only DECOMPOSES Performance into a
                    site-capacity part and a speed part; it never changes OEE (closures already
                    lower Performance because output is judged against the full-capacity ideal)

Status
  BLOCKED  a factor cannot be computed yet -> no OEE number (current state of this project:
           run-state, output, good-unit and cycle-time data do not exist)
  INVALID  an input is impossible (negative, good > output, run > planned, Performance > 100% ...)
           -> no OEE number, exit code 2
  OK       OEE reported; it is cross-checked against good x ideal_cycle / planned

Zero cases: run_min = 0 with no output -> OEE = 0 (P and Q undefined); output = 0 with run time -> P = 0,
Q undefined, OEE = 0.

Usage:
    python oee_calculator.py --demo      # the guide's simulator example (illustrative, NOT handler data)
    python oee_calculator.py --run-min 400 --planned-min 480 --output 380 --good 370 --ideal-cycle-min 1.0
"""

import argparse
import sys

TOL = 1e-9


def validate(run_min=None, planned_min=None, output=None, good=None, ideal_cycle_min=None, site_availability=None) -> list[str]:
    errors = []
    named = dict(run_min=run_min, planned_min=planned_min, output=output, good=good, ideal_cycle_min=ideal_cycle_min)
    for k, v in named.items():
        if v is not None and v < 0:
            errors.append(f"{k} is negative ({v})")
    if planned_min is not None and planned_min == 0:
        errors.append("planned_min must be > 0 (it is the denominator of Availability)")
    if ideal_cycle_min is not None and ideal_cycle_min == 0:
        errors.append("ideal_cycle_min must be > 0")
    if run_min is not None and planned_min and run_min > planned_min:
        errors.append(f"run_min ({run_min}) exceeds planned_min ({planned_min}): Availability would be above 100%")
    if good is not None and output is not None and good > output:
        errors.append(f"good ({good}) exceeds output ({output}): Quality would be above 100%")
    if run_min == 0 and output:
        errors.append(f"output ({output}) with run_min = 0: units cannot be tested without run time")
    if None not in (run_min, output, ideal_cycle_min) and run_min > 0 and output * ideal_cycle_min > run_min * (1 + TOL):
        errors.append(f"Performance would be {output * ideal_cycle_min / run_min * 100:.1f}% (> 100%): output is faster than the ideal cycle time - check ideal_cycle_min")
    if site_availability is not None and not 0 <= site_availability <= 1:
        errors.append(f"site_availability ({site_availability}) must be between 0 and 1")
    return errors


def oee(run_min=None, planned_min=None, output=None, good=None, ideal_cycle_min=None, site_availability=None):
    res = {"availability": None, "performance": None, "quality": None, "oee": None, "site_availability": site_availability,
           "complete": False, "missing": [], "errors": [], "notes": [], "status": "BLOCKED", "capacity_split": None}

    res["errors"] = validate(run_min, planned_min, output, good, ideal_cycle_min, site_availability)
    if res["errors"]:
        res["status"] = "INVALID"
        return res

    if run_min is not None and planned_min:
        res["availability"] = run_min / planned_min
    if None not in (run_min, output, ideal_cycle_min):
        if run_min > 0:
            res["performance"] = output * ideal_cycle_min / run_min
    if None not in (good, output) and output > 0:
        res["quality"] = good / output

    missing = []
    if run_min is None or planned_min is None:
        missing.append("availability")
    if run_min is None or output is None or ideal_cycle_min is None:
        missing.append("performance")
    if good is None or output is None:
        missing.append("quality")
    res["missing"] = missing
    if missing:
        return res  # BLOCKED: no OEE number, partial products are never reported

    res["complete"], res["status"] = True, "OK"
    if run_min == 0:
        res["oee"] = 0.0
        res["notes"].append("no run time: P and Q are undefined and OEE = 0")
    elif output == 0:
        res["oee"] = 0.0
        res["notes"].append("no output: Q is undefined and OEE = 0")
    else:
        res["oee"] = res["availability"] * res["performance"] * res["quality"]

    expected = good * ideal_cycle_min / planned_min  # A x P x Q simplifies to this
    if abs(res["oee"] - expected) > 1e-9:
        res["errors"].append(f"self-check failed: OEE {res['oee']:.9f} != good x ideal_cycle / planned {expected:.9f}")
        res["status"], res["oee"] = "INVALID", None
        return res

    if site_availability and res["performance"] is not None:
        speed = res["performance"] / site_availability
        res["capacity_split"] = {"site_capacity": site_availability, "speed_and_other": speed}
        if speed > 1 + TOL:
            res["notes"].append("speed/other factor above 100%: site availability may be understated or ideal_cycle_min too large")
    return res


def show(res) -> int:
    pct = lambda x: "n/a" if x is None else f"{x * 100:.1f}%"
    print(f"Availability (A): {pct(res['availability'])}")
    print(f"Performance  (P): {pct(res['performance'])}")
    print(f"Quality      (Q): {pct(res['quality'])}")
    if res["status"] == "INVALID":
        print("OEE: INVALID - no number reported")
        for e in res["errors"]:
            print(f"  ERROR: {e}")
        return 2
    if res["status"] == "BLOCKED":
        if res["site_availability"] is not None:
            print(f"Site availability (capacity factor, not time): {pct(res['site_availability'])}")
        print(f"OEE: BLOCKED - missing {', '.join(res['missing'])} (needs run-state, output, good-unit and cycle-time data)")
        return 0
    print(f"OEE: {pct(res['oee'])}")
    for n in res["notes"]:
        print(f"  note: {n}")
    if res["capacity_split"]:
        c = res["capacity_split"]
        print(f"  Performance = site capacity {pct(c['site_capacity'])} x speed/other {pct(c['speed_and_other'])} (decomposition only; OEE unchanged)")
    return 0


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
    vals = {k: v for k, v in vars(args).items() if k != "demo"}
    if args.demo or all(v is None for v in vals.values()):
        print("DEMO: the guide's simulator example - illustrative numbers, NOT handler data.")
        print("      The screenshot shows no cycle time; 1.0 min/unit is back-solved (400 x 0.95 / 380) so that P = 95.0%.")
        sys.exit(show(oee(400, 480, 380, 370, 400 * 0.95 / 380)))
    sys.exit(show(oee(args.run_min, args.planned_min, args.output, args.good, args.ideal_cycle_min, args.site_availability)))


if __name__ == "__main__":
    main()
