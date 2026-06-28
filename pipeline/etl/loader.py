"""
pipeline/etl/loader.py
Creates the 3-layer schema (raw, staging, analytics) and aggregates
staging data into the analytics layer for trend queries.
Run with --migrate flag to apply schema, then without to load data.
"""

import os
import sys
import logging
import datetime
from sqlalchemy import create_engine, text

logging.basicConfig(
    filename=f"logs/transform_{datetime.date.today()}.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)

SCHEMA_SQL = """
-- RAW LAYER: exact snapshots as ingested, never modified
CREATE TABLE IF NOT EXISTS raw_snapshots (
    id           SERIAL PRIMARY KEY,
    device_id    INTEGER,
    hostname     TEXT NOT NULL,
    vendor       TEXT NOT NULL,
    raw_config   TEXT NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW()
);

-- STAGING LAYER: parsed and scored compliance records
CREATE TABLE IF NOT EXISTS stg_compliance (
    id               SERIAL PRIMARY KEY,
    raw_snapshot_id  INTEGER UNIQUE REFERENCES raw_snapshots(id),
    device_id        INTEGER,
    hostname         TEXT NOT NULL,
    vendor           TEXT NOT NULL,
    score            FLOAT NOT NULL,
    violations       JSONB DEFAULT '[]',
    collected_at     TIMESTAMPTZ
);

-- ANALYTICS LAYER: daily aggregated fleet metrics
CREATE TABLE IF NOT EXISTS analytics_fleet_daily (
    id              SERIAL PRIMARY KEY,
    report_date     DATE NOT NULL,
    vendor          TEXT NOT NULL,
    avg_score       FLOAT,
    min_score       FLOAT,
    max_score       FLOAT,
    device_count    INTEGER,
    violation_count INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (report_date, vendor)
);

-- ANALYTICS LAYER: per-device daily scores for trend lines
CREATE TABLE IF NOT EXISTS analytics_device_daily (
    id           SERIAL PRIMARY KEY,
    report_date  DATE NOT NULL,
    device_id    INTEGER,
    hostname     TEXT NOT NULL,
    vendor       TEXT NOT NULL,
    avg_score    FLOAT,
    min_score    FLOAT,
    violations   INTEGER,
    UNIQUE (report_date, device_id)
);

CREATE INDEX IF NOT EXISTS idx_stg_collected ON stg_compliance(collected_at);
CREATE INDEX IF NOT EXISTS idx_stg_device    ON stg_compliance(device_id);
CREATE INDEX IF NOT EXISTS idx_fleet_date    ON analytics_fleet_daily(report_date);
"""


def migrate():
    log.info("Applying schema migrations")
    with engine.connect() as conn:
        conn.execute(text(SCHEMA_SQL))
        conn.commit()
    log.info("Schema ready")


def load_fleet_daily():
    """Aggregate yesterday's staging data into analytics_fleet_daily."""
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO analytics_fleet_daily
                (report_date, vendor, avg_score, min_score, max_score, device_count, violation_count)
            SELECT
                DATE(collected_at)          AS report_date,
                vendor,
                AVG(score)                  AS avg_score,
                MIN(score)                  AS min_score,
                MAX(score)                  AS max_score,
                COUNT(DISTINCT device_id)   AS device_count,
                SUM(jsonb_array_length(violations)) AS violation_count
            FROM stg_compliance
            WHERE DATE(collected_at) = CURRENT_DATE - INTERVAL '1 day'
            GROUP BY DATE(collected_at), vendor
            ON CONFLICT (report_date, vendor) DO UPDATE SET
                avg_score       = EXCLUDED.avg_score,
                min_score       = EXCLUDED.min_score,
                max_score       = EXCLUDED.max_score,
                device_count    = EXCLUDED.device_count,
                violation_count = EXCLUDED.violation_count
        """))

        conn.execute(text("""
            INSERT INTO analytics_device_daily
                (report_date, device_id, hostname, vendor, avg_score, min_score, violations)
            SELECT
                DATE(collected_at)          AS report_date,
                device_id,
                hostname,
                vendor,
                AVG(score)                  AS avg_score,
                MIN(score)                  AS min_score,
                SUM(jsonb_array_length(violations)) AS violations
            FROM stg_compliance
            WHERE DATE(collected_at) = CURRENT_DATE - INTERVAL '1 day'
            GROUP BY DATE(collected_at), device_id, hostname, vendor
            ON CONFLICT (report_date, device_id) DO UPDATE SET
                avg_score  = EXCLUDED.avg_score,
                min_score  = EXCLUDED.min_score,
                violations = EXCLUDED.violations
        """))
        conn.commit()
    log.info("Analytics layer loaded")


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    if "--migrate" in sys.argv:
        migrate()
    else:
        load_fleet_daily()
