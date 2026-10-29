-- Dashboard data model: THE single source of truth (TimescaleDB / PostgreSQL dialect).
-- 04-data-storytelling-visualization/dashboard-specification/scripts/build_dashboard_db.py derives a SQLite
-- copy from this file (types translated, arrays stored as JSON text) so panel queries can be dry-run.
-- Keep the status list equal to lib/contactor_io.py; dashboard_spec_check.py verifies it.

CREATE TABLE IF NOT EXISTS contactor_samples (
    ts            timestamptz NOT NULL,
    handler       text        NOT NULL,
    side          text        NOT NULL CHECK (side IN ('front','rear')),
    err_01        integer,
    closed_sites  integer[]   NOT NULL DEFAULT '{}',   -- cleaned list; empty for dropped readings
    status        text        NOT NULL CHECK (status IN ('OK','NA_ZERO','READ_FAIL_256','READ_FAIL_NEAR_FULL','READ_FAIL_GAP','NA_NONZERO')),
    valid         boolean     NOT NULL,                -- OK or NA_ZERO
    weight_min    real        NOT NULL,                -- minutes the reading represents (capped at 15)
    PRIMARY KEY (handler, side, ts)
);
SELECT create_hypertable('contactor_samples', 'ts', if_not_exists => TRUE);

-- one row per closure of one site (debounced); replaces the old per-transition table
CREATE TABLE IF NOT EXISTS closure_episodes (
    handler        text        NOT NULL,
    side           text        NOT NULL,
    site           integer     NOT NULL,
    start_ts       timestamptz NOT NULL,
    end_ts         timestamptz NOT NULL,
    duration_min   real        NOT NULL,
    ongoing        boolean     NOT NULL,
    left_censored  boolean     NOT NULL
);

-- spatially connected episodes that start together
CREATE TABLE IF NOT EXISTS closure_events (
    event_id       integer     NOT NULL,
    handler        text        NOT NULL,
    side           text        NOT NULL,
    start_ts       timestamptz NOT NULL,
    end_ts         timestamptz NOT NULL,
    duration_min   real        NOT NULL,
    n_sites        integer     NOT NULL,
    sites          integer[]   NOT NULL,
    block_aligned  real        NOT NULL,
    n_blocks_2x2   integer     NOT NULL,
    ongoing        boolean     NOT NULL,
    left_censored  boolean     NOT NULL,
    PRIMARY KEY (handler, side, event_id)
);

-- per-site closure share over the period and the last window_days, with the recency status
CREATE TABLE IF NOT EXISTS site_recency (
    as_of         timestamptz NOT NULL,
    handler       text        NOT NULL,
    side          text        NOT NULL,
    site          integer     NOT NULL,
    window_days   integer     NOT NULL,
    share_period  real        NOT NULL,
    share_recent  real        NOT NULL,
    status        text        NOT NULL CHECK (status IN ('PERSISTENT','NEW','CURRENT','INTERMITTENT','RESOLVED','-')),
    PRIMARY KEY (handler, side, site, as_of)
);

CREATE TABLE IF NOT EXISTS equipment_daily_metrics (
    day                date    NOT NULL,
    handler            text    NOT NULL,
    side               text    NOT NULL,
    site_availability  real,   -- upper bound, percent (list-length closures)
    availability_low   real,   -- lower bound, percent (max(err_01, list) closures)
    valid_samples      integer,
    total_samples      integer,
    fail_pct           real,   -- share of the day's readings that were dropped
    coverage_pct       real,   -- total_samples / ~360 expected per day
    PRIMARY KEY (handler, side, day)
);

CREATE TABLE IF NOT EXISTS capacity_summary (
    period_start     date    NOT NULL,
    period_end       date    NOT NULL,
    handler          text    NOT NULL,
    side             text    NOT NULL,
    availability     real    NOT NULL,   -- percent, time-weighted
    availability_low real    NOT NULL,
    ci_low           real    NOT NULL,   -- 95% day-bootstrap plausible range
    ci_high          real    NOT NULL,
    closed_now       integer NOT NULL,   -- sites closed >= 50% of the last recent_days
    recent_days      integer NOT NULL,
    PRIMARY KEY (handler, side, period_end)
);
