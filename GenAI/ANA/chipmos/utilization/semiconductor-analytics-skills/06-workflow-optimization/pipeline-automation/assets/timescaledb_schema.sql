-- TimescaleDB / PostgreSQL schema for handler contactor utilization
CREATE TABLE IF NOT EXISTS contactor_samples (
    ts            timestamptz NOT NULL,
    handler       text        NOT NULL,
    side          text        NOT NULL CHECK (side IN ('front','rear')),
    err_01        integer,
    closed_sites  integer[]   NOT NULL DEFAULT '{}',
    status        text        NOT NULL,      -- OK | NA_ZERO | READ_FAIL_256 | READ_FAIL_NEAR_FULL | NA_NONZERO
    weight_min    real        NOT NULL,
    PRIMARY KEY (handler, side, ts)
);
SELECT create_hypertable('contactor_samples', 'ts', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS site_state_events (
    ts        timestamptz NOT NULL,
    handler   text        NOT NULL,
    side      text        NOT NULL,
    site      integer     NOT NULL,
    event     text        NOT NULL CHECK (event IN ('CLOSED','OPENED')),
    event_id  bigint
);

CREATE TABLE IF NOT EXISTS equipment_daily_metrics (
    day                date NOT NULL,
    handler            text NOT NULL,
    side               text NOT NULL,
    site_availability  real,   -- high bound (list length)
    availability_low   real,   -- low bound (max(err_01, list))
    valid_samples      integer,
    PRIMARY KEY (handler, side, day)
);

-- Grafana: daily availability panel
-- SELECT day AS time, side, site_availability*100 AS availability FROM equipment_daily_metrics WHERE $__timeFilter(day) ORDER BY 1;
