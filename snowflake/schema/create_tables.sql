-- NetGuard — 3-Layer Analytics Schema
-- Mirrors the Snowflake medallion architecture (raw → staging → analytics)
-- running on PostgreSQL for the free/GitHub version.
-- If connecting a real Snowflake account, these DDLs work there too.

-- ─────────────────────────────────────────────────────────────────────────────
-- RAW LAYER
-- Exact snapshots as ingested. Never modified after insert.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS raw_snapshots (
    id           SERIAL PRIMARY KEY,
    device_id    INTEGER,
    hostname     TEXT        NOT NULL,
    vendor       TEXT        NOT NULL,  -- 'cisco' | 'juniper'
    raw_config   TEXT        NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    pipeline_run TEXT                              -- GitHub Actions run ID
);

CREATE INDEX IF NOT EXISTS idx_raw_device      ON raw_snapshots(device_id);
CREATE INDEX IF NOT EXISTS idx_raw_collected   ON raw_snapshots(collected_at);
CREATE INDEX IF NOT EXISTS idx_raw_vendor      ON raw_snapshots(vendor);

-- ─────────────────────────────────────────────────────────────────────────────
-- STAGING LAYER
-- Parsed, cleaned, and scored compliance records.
-- One row per raw snapshot after transformation.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS stg_compliance (
    id               SERIAL PRIMARY KEY,
    raw_snapshot_id  INTEGER     UNIQUE REFERENCES raw_snapshots(id),
    device_id        INTEGER,
    hostname         TEXT        NOT NULL,
    vendor           TEXT        NOT NULL,
    score            FLOAT       NOT NULL CHECK (score BETWEEN 0 AND 100),
    violations       JSONB       NOT NULL DEFAULT '[]',
    violation_count  INTEGER     GENERATED ALWAYS AS (jsonb_array_length(violations)) STORED,
    collected_at     TIMESTAMPTZ NOT NULL,
    processed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stg_device      ON stg_compliance(device_id);
CREATE INDEX IF NOT EXISTS idx_stg_collected   ON stg_compliance(collected_at);
CREATE INDEX IF NOT EXISTS idx_stg_score       ON stg_compliance(score);
CREATE INDEX IF NOT EXISTS idx_stg_vendor      ON stg_compliance(vendor);

-- ─────────────────────────────────────────────────────────────────────────────
-- ANALYTICS LAYER
-- Pre-aggregated tables for fast dashboard and report queries.
-- ─────────────────────────────────────────────────────────────────────────────

-- Daily fleet-wide metrics (one row per vendor per day)
CREATE TABLE IF NOT EXISTS analytics_fleet_daily (
    id              SERIAL PRIMARY KEY,
    report_date     DATE    NOT NULL,
    vendor          TEXT    NOT NULL,
    avg_score       FLOAT,
    min_score       FLOAT,
    max_score       FLOAT,
    device_count    INTEGER,
    violation_count INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (report_date, vendor)
);

-- Daily per-device scores for trend lines
CREATE TABLE IF NOT EXISTS analytics_device_daily (
    id           SERIAL PRIMARY KEY,
    report_date  DATE    NOT NULL,
    device_id    INTEGER NOT NULL,
    hostname     TEXT    NOT NULL,
    vendor       TEXT    NOT NULL,
    avg_score    FLOAT,
    min_score    FLOAT,
    violations   INTEGER,
    UNIQUE (report_date, device_id)
);

-- Anomaly alerts table
CREATE TABLE IF NOT EXISTS anomaly_alerts (
    id           SERIAL PRIMARY KEY,
    device_id    INTEGER,
    hostname     TEXT,
    vendor       TEXT,
    alert_type   TEXT,        -- 'score_drop' | 'violation_spike' | 'new_violation'
    detail       JSONB,
    detected_at  TIMESTAMPTZ  DEFAULT NOW(),
    acknowledged BOOLEAN      DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_fleet_date      ON analytics_fleet_daily(report_date);
CREATE INDEX IF NOT EXISTS idx_device_date     ON analytics_device_daily(report_date);
CREATE INDEX IF NOT EXISTS idx_device_hostname ON analytics_device_daily(hostname);
CREATE INDEX IF NOT EXISTS idx_alerts_ack      ON anomaly_alerts(acknowledged);
