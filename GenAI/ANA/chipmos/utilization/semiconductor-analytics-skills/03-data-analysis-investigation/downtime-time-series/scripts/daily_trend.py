"""
Daily availability trend with data-quality context, robust anomaly flags, a level-shift test
and a time-weighted hour-of-day profile with standard errors.

  * daily table: time-weighted availability, 7-day rolling mean, valid samples, failure rate,
    coverage; days with a failure rate >= --dq-pct are marked so a dip caused by bad reads is
    not mistaken for an equipment event
  * anomaly flag: robust z-score (median/MAD) with default threshold 2.5 (A20); the script also
    prints the deviation in points a day needs to be flagged and the number of flags expected
    by chance. A 3.5 threshold cannot fire on 32 days with ~2 pt daily noise
  * level shift: best single split (>= 7 days each side) by Welch t, p-value from a permutation
    test of the maximum |t| over splits (days treated as exchangeable)
  * hour of day: within-day effect (each hour vs that day's own mean) with standard error;
    hours beyond 2 SE are listed next to the number expected by chance (~1 of 24); the test is
    repeated without readings that have >= --burst-closed closed sites (default 60) because bursts of
    implausibly large closed sets can masquerade as a time-of-day effect

Usage:
    python daily_trend.py --side front
    python daily_trend.py --side rear --z 2.5 --dq-pct 5
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import contactor_io as cio  # noqa: E402

DEFAULT_Z = 2.5
EXPECTED_PER_DAY = 360  # ~4 min cadence


def daily_series(df: pd.DataFrame) -> pd.DataFrame:
    v = df[df["valid"]].copy()
    v["day"] = pd.to_datetime(v["timestamp"].dt.date)
    g = v.groupby("day").apply(
        lambda x: pd.Series({
            "availability_pct": (1 - (x["n_closed"] * x["weight_min"]).sum() / (256 * x["weight_min"].sum())) * 100,
            "median_closed": x["n_closed"].median(),
            "valid_samples": len(x),
        }),
        include_groups=False,
    )
    total = df.groupby(pd.to_datetime(df["timestamp"].dt.date)).size()
    g["fail_pct"] = ((1 - g["valid_samples"] / total.reindex(g.index)) * 100).round(1)
    g["coverage_pct"] = (total.reindex(g.index) / EXPECTED_PER_DAY * 100).round(0)
    g["rolling7_pct"] = g["availability_pct"].rolling(7, min_periods=3).mean()
    g["valid_samples"] = g["valid_samples"].astype(int)
    return g.round(2)


def robust_z(s: pd.Series) -> pd.Series:
    med = s.median()
    mad = (s - med).abs().median() or 1e-9
    return 0.6745 * (s - med) / mad


def robust_flags(s: pd.Series, z: float = DEFAULT_Z) -> pd.Series:
    return robust_z(s).abs() > z


def detection_floor(s: pd.Series, z: float) -> float:
    """Deviation from the median (in points) a day needs to be flagged at threshold z."""
    mad = (s - s.median()).abs().median() or 1e-9
    return z * mad / 0.6745


def level_shift(s: pd.Series, min_seg: int = 7, n_perm: int = 2000, seed: int = 0) -> dict | None:
    """Best single split by Welch t; p-value = permutation test of max |t| over all splits."""
    x = s.to_numpy(dtype=float)
    n = len(x)
    if n < 2 * min_seg + 1:
        return None

    def best(arr):
        top_t, top_k = 0.0, min_seg
        for k in range(min_seg, n - min_seg + 1):
            a, b = arr[:k], arr[k:]
            se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
            t = (b.mean() - a.mean()) / se if se > 0 else 0.0
            if abs(t) > abs(top_t):
                top_t, top_k = t, k
        return top_t, top_k

    t0, k0 = best(x)
    rng = np.random.default_rng(seed)
    hits = sum(abs(best(rng.permutation(x))[0]) >= abs(t0) for _ in range(n_perm))
    return {
        "split_day": s.index[k0].date(),
        "before_pct": round(float(x[:k0].mean()), 2),
        "after_pct": round(float(x[k0:].mean()), 2),
        "diff_pts": round(float(x[k0:].mean() - x[:k0].mean()), 2),
        "t": round(t0, 2),
        "p_value": round((hits + 1) / (n_perm + 1), 3),
    }


def hour_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Within-day hour-of-day effect.

    Per day and hour: time-weighted availability. Each hour is compared with that day's own mean
    (removes between-day level differences, which would otherwise leak into single hours);
    effect = mean deviation over days in points, SE from the day-to-day spread of that deviation.
    """
    v = df[df["valid"]].copy()
    v["day"] = v["timestamp"].dt.date
    v["hour"] = v["timestamp"].dt.hour
    v["cw"] = v["n_closed"] * v["weight_min"]
    g = v.groupby(["day", "hour"]).agg(cw=("cw", "sum"), w=("weight_min", "sum"))
    t = (1 - g["cw"] / (256 * g["w"])).mul(100).unstack()
    dev = t.sub(t.mean(axis=1), axis=0)
    eff, se = dev.mean(), dev.std() / np.sqrt(dev.count())
    z = eff / se
    return pd.DataFrame({"availability_pct": t.mean().round(2), "effect_pts": eff.round(2), "se": se.round(2),
                         "z": z.round(1), "beyond_2se": z.abs() > 2})


def main():
    ap = argparse.ArgumentParser(description="Daily availability trend")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--side", choices=["front", "rear"], default="front")
    ap.add_argument("--start", default=cio.DEFAULT_START)
    ap.add_argument("--near-full-min", type=int, default=cio.NEAR_FULL_MIN)
    ap.add_argument("--z", type=float, default=DEFAULT_Z, help="robust z threshold for anomaly flags")
    ap.add_argument("--dq-pct", type=float, default=5.0, help="mark days with at least this failure rate")
    ap.add_argument("--burst-closed", type=int, default=60, help="robustness check: drop readings with at least this many closed sites")
    args = ap.parse_args()

    df = cio.load_side(args.side, args.data_dir, args.start, near_full_min=args.near_full_min)
    ts = daily_series(df)
    s = ts["availability_pct"]
    flags = robust_flags(s, args.z)
    ts["anomaly"] = ["<-- check" if f else "" for f in flags]
    ts["data_quality"] = ["bad reads?" if p >= args.dq_pct else "" for p in ts["fail_pct"]]
    print(f"\n=== {args.side.upper()} daily availability ===")
    print(ts.to_string())

    floor = detection_floor(s, args.z)
    exp = len(s) * math.erfc(args.z / math.sqrt(2))
    print(f"\nanomaly rule: robust z > {args.z}; a day needs |deviation from median {s.median():.2f}%| > {floor:.1f} pts")
    print(f"flagged {int(flags.sum())} of {len(s)} days (about {exp:.1f} expected by chance if the series were normal)")
    dq_flagged = [str(d.date()) for d in ts.index[flags & (ts['fail_pct'] >= args.dq_pct)]]
    if dq_flagged:
        print(f"flagged days that also have a high failure rate (check data quality first): {dq_flagged}")

    ls = level_shift(s)
    print("\n=== level shift (best single split, >= 7 days each side) ===")
    if ls:
        print(f"split at {ls['split_day']}: before {ls['before_pct']}% -> after {ls['after_pct']}% (diff {ls['diff_pts']:+} pts, t={ls['t']}, permutation p={ls['p_value']})")
        print("interpretation: p < 0.05 suggests a real level shift; otherwise treat the series as flat plus noise")
    else:
        print("too few days")

    hp = hour_profile(df)
    print("\n=== hour-of-day effect: each hour vs the same day's mean (time-weighted), pts ===")
    print(hp.to_string())
    print(f"hours with an effect beyond 2 SE: {int(hp['beyond_2se'].sum())} of 24 (about 1.1 expected by chance)")
    burst = df["valid"] & (df["n_closed"] >= args.burst_closed)
    hp2 = hour_profile(df.assign(valid=df["valid"] & ~burst))
    print(f"excluding readings with >= {args.burst_closed} closed sites ({int(burst.sum())} readings, {burst.sum() / df['valid'].sum() * 100:.1f}% of valid): "
          f"{int(hp2['beyond_2se'].sum())} of 24 hours beyond 2 SE")
    if hp["beyond_2se"].sum() > 2 and hp2["beyond_2se"].sum() <= 2:
        low = hp["effect_pts"].sort_values().head(4).index.tolist()
        print(f"-> the hour pattern is driven by large-closure bursts (lowest hours {sorted(low)}), not a steady time-of-day effect; "
              "check them against run-state / screenshots (capture artefact vs real event)")


if __name__ == "__main__":
    main()
