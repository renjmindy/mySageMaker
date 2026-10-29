"""
Shared loader for Advantest handler contactor-site logs (front / rear).

Every skill script in this repo imports from here so the cleaning rules are
defined exactly once. Each rule has an id in the assumptions log
(02-documentation-knowledge/analysis-assumptions-log/assumptions.json), which records
whether the process owner confirmed it or it is only applied:

  * err_01 is the number of CLOSED (non-functional / grey) sites
  * err_02 is a ';'-separated list of closed site IDs
  * front = sites 1-256, rear = sites 257-512 (16 columns x 32 rows overall)
  * err_01 == 256            -> read failure, sample is dropped
  * err_02 == N/A, err_01==0 -> genuinely zero closed sites (kept)
  * err_02 == N/A, err_01>0  -> unreadable list, sample is dropped
  * list length is trusted over err_01 (the count is the noisier field)
    NOTE: in practice err_01 is never LOWER than the list length, so list
    length is a lower bound on closures - see references/log_semantics.md
  * err_01 in 252-255 is also a read failure (confirmed); `near_full_min`
    defaults to NEAR_FULL_MIN = 252 and can be set to 0/None to disable
  * err_01 exceeding the cleaned list length by more than MAX_COUNT_GAP (50)
    means the list does not support the count (unreadable list) -> sample is
    dropped (status READ_FAIL_GAP); `max_count_gap` 0/None disables
  * IDs outside the side's range and duplicate IDs are OCR noise and removed
  * only Sep/Oct 2026 production data is analysed (07/30 was a trial run)
"""

from __future__ import annotations

import glob
import os
import re
from pathlib import Path

import pandas as pd

SIDES = {
    "front": {"lo": 1, "hi": 256, "pattern": "contactor_2026*.csv"},
    "rear": {"lo": 257, "hi": 512, "pattern": "contactor_rear_2026*.csv"},
}
COLS = 16
REQUIRED_COLUMNS = ("Timestamp", "err_01", "err_02")
SITES_PER_SIDE = 256
READ_FAIL_COUNT = 256
NEAR_FULL_MIN = 252  # err_01 252-255 = read failure (confirmed by process owner)
MAX_COUNT_GAP = 50   # err_01 - len(list) above this = list unreadable (agreed with process owner)
DEFAULT_START = "2026-09-01"
DEFAULT_MAX_GAP_MIN = 15.0  # a sample never represents more than this many minutes

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT.parent / "dat"


class DataFormatError(ValueError):
    """A CSV does not have the expected columns or values; raised instead of continuing silently."""


def site_row_col(site: int) -> tuple[int, int]:
    """Row (1-32) and column (1-16) on the Contactor Select screen."""
    return (site - 1) // COLS + 1, (site - 1) % COLS + 1


def _parse_ids(text: str, lo: int, hi: int) -> tuple[list[int], int, int]:
    raw = [int(t) for t in text.split(";") if t.strip().isdigit()]
    valid = sorted({x for x in raw if lo <= x <= hi})
    out_of_range = sum(1 for x in raw if not lo <= x <= hi)
    duplicates = len(raw) - len(set(raw))
    return valid, out_of_range, duplicates


def load_side(
    side: str,
    data_dir: str | os.PathLike | None = None,
    start: str = DEFAULT_START,
    end: str | None = None,
    max_gap_min: float = DEFAULT_MAX_GAP_MIN,
    near_full_min: int | None = NEAR_FULL_MIN,
    max_count_gap: int | None = MAX_COUNT_GAP,
) -> pd.DataFrame:
    """Load one side with per-row status, cleaned site list and time weight.

    Columns: timestamp, err_01, status, sites, n_closed, n_oob, n_dup,
             count_mismatch, weight_min, valid
    attrs: duplicate_timestamps, file_date_mismatch (rows whose timestamp day differs from the file's
           day), source_rows, files - facts the cleaning would otherwise hide
    Raises DataFormatError for a missing column, an unparseable Timestamp or a non-numeric err_01.
    status: OK | NA_ZERO | READ_FAIL_256 | READ_FAIL_NEAR_FULL | READ_FAIL_GAP | NA_NONZERO
    """
    cfg = SIDES[side]
    data_dir = Path(data_dir or DEFAULT_DATA_DIR)
    files = sorted(glob.glob(str(data_dir / cfg["pattern"])))
    if not files:
        raise FileNotFoundError(f"no {side} CSVs matching {cfg['pattern']} in {data_dir}")

    frames = []
    for f in files:
        raw = pd.read_csv(f, encoding="utf-8-sig", dtype=str, keep_default_na=False)
        missing = [c for c in REQUIRED_COLUMNS if c not in raw.columns]
        if missing:
            raise DataFormatError(f"{Path(f).name}: missing column(s) {missing}; found {list(raw.columns)}")
        m = re.search(r"(\d{8})\.csv$", f)
        raw["_file_date"] = m.group(1) if m else ""
        frames.append(raw)
    df = pd.concat(frames, ignore_index=True)
    try:
        df["timestamp"] = pd.to_datetime(df["Timestamp"], format="%Y/%m/%d %H:%M")
    except ValueError as e:
        raise DataFormatError(f"unparseable Timestamp value: {e}") from e
    df = df[df["timestamp"] >= pd.Timestamp(start)]
    if end:
        df = df[df["timestamp"] <= pd.Timestamp(end) + pd.Timedelta(days=1)]
    # facts about the source that the cleaning would otherwise hide (see data_gate.py)
    duplicates = int(df.duplicated("timestamp").sum())
    day_mismatch = int((df["timestamp"].dt.strftime("%Y%m%d") != df["_file_date"]).sum())
    source_rows = len(df)
    df = df.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    counts = pd.to_numeric(df["err_01"], errors="coerce")
    if counts.isna().any():
        raise DataFormatError(f"err_01 has {int(counts.isna().sum())} non-numeric value(s)")
    df["err_01"] = counts.astype(int)

    status, sites, n_oob, n_dup = [], [], [], []
    for cnt, lst in zip(df["err_01"], df["err_02"].str.strip()):
        if cnt == READ_FAIL_COUNT:
            status.append("READ_FAIL_256"); ids, oob, dup = [], 0, 0
        elif lst == "N/A":
            if cnt == 0:
                status.append("NA_ZERO")
            else:
                status.append("NA_NONZERO")
            ids, oob, dup = [], 0, 0
        elif near_full_min and cnt >= near_full_min:
            status.append("READ_FAIL_NEAR_FULL"); ids, oob, dup = [], 0, 0
        else:
            ids, oob, dup = _parse_ids(lst, cfg["lo"], cfg["hi"])
            if max_count_gap and cnt - len(ids) > max_count_gap:
                status.append("READ_FAIL_GAP"); ids, oob, dup = [], 0, 0
            else:
                status.append("OK")
        sites.append(ids); n_oob.append(oob); n_dup.append(dup)

    df["status"], df["sites"], df["n_oob"], df["n_dup"] = status, sites, n_oob, n_dup
    df["n_closed"] = df["sites"].map(len)
    df["valid"] = df["status"].isin(["OK", "NA_ZERO"])
    df["count_mismatch"] = df["valid"] & (df["n_closed"] != df["err_01"])

    gap = df["timestamp"].diff().shift(-1).dt.total_seconds().div(60)
    typical = float(gap.median()) if gap.notna().any() else 4.0
    df["weight_min"] = gap.fillna(typical).clip(upper=max_gap_min)
    out = df[["timestamp", "err_01", "status", "sites", "n_closed", "n_oob", "n_dup",
              "count_mismatch", "weight_min", "valid"]]
    out.attrs.update(duplicate_timestamps=duplicates, file_date_mismatch=day_mismatch, source_rows=source_rows,
                     files=[Path(f).name for f in files])
    return out


def load_all(data_dir=None, start: str = DEFAULT_START, end: str | None = None,
             near_full_min: int | None = NEAR_FULL_MIN,
             max_count_gap: int | None = MAX_COUNT_GAP) -> dict[str, pd.DataFrame]:
    return {s: load_side(s, data_dir, start, end, near_full_min=near_full_min, max_count_gap=max_count_gap) for s in SIDES}


def weighted_availability(df: pd.DataFrame) -> float:
    """Time-weighted share of the 256 sites that are open, over valid samples (0-1)."""
    v = df[df["valid"]]
    if v.empty:
        return float("nan")
    return 1 - float((v["n_closed"] * v["weight_min"]).sum() / v["weight_min"].sum()) / SITES_PER_SIDE


def closed_matrix(df: pd.DataFrame, side: str) -> pd.DataFrame:
    """Boolean matrix (valid samples x sites) - True where the site is closed."""
    import numpy as np
    cfg = SIDES[side]
    v = df[df["valid"]].reset_index(drop=True)
    sites = np.arange(cfg["lo"], cfg["hi"] + 1)
    mat = np.zeros((len(v), len(sites)), dtype=bool)
    for i, ids in enumerate(v["sites"]):
        for s in ids:
            mat[i, s - cfg["lo"]] = True
    out = pd.DataFrame(mat, columns=sites)
    out.insert(0, "timestamp", v["timestamp"].values)
    out.insert(1, "weight_min", v["weight_min"].values)
    return out.set_index("timestamp")
