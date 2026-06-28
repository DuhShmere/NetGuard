"""
pipeline/etl/quality.py
Runs data quality assertions after each transform/load cycle.
Fails loudly (non-zero exit) so GitHub Actions marks the job as failed.
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


def assert_no_nulls():
    """Critical fields must never be null in stg_compliance."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM stg_compliance
            WHERE device_id IS NULL OR score IS NULL OR collected_at IS NULL
        """)).scalar()
    if result > 0:
        raise AssertionError(f"Null check failed: {result} rows with null critical fields")
    log.info(f"Null check passed")


def assert_score_range():
    """Compliance scores must be between 0 and 100."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM stg_compliance
            WHERE score < 0 OR score > 100
        """)).scalar()
    if result > 0:
        raise AssertionError(f"Score range check failed: {result} scores out of 0-100 range")
    log.info("Score range check passed")


def assert_no_duplicates():
    """Each raw snapshot should only appear once in staging."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT raw_snapshot_id, COUNT(*) AS cnt
                FROM stg_compliance
                GROUP BY raw_snapshot_id
                HAVING COUNT(*) > 1
            ) dupes
        """)).scalar()
    if result > 0:
        raise AssertionError(f"Duplicate check failed: {result} raw snapshots appear more than once")
    log.info("Duplicate check passed")


def assert_row_counts():
    """Staging should have at least as many rows as raw (all raws processed)."""
    with engine.connect() as conn:
        raw_count = conn.execute(text("SELECT COUNT(*) FROM raw_snapshots")).scalar()
        stg_count = conn.execute(text("SELECT COUNT(*) FROM stg_compliance")).scalar()
    if stg_count < raw_count * 0.95:
        raise AssertionError(
            f"Row count check failed: {stg_count} staged vs {raw_count} raw (>5% unprocessed)"
        )
    log.info(f"Row count check passed: {stg_count} staged / {raw_count} raw")


def run():
    checks = [assert_no_nulls, assert_score_range, assert_no_duplicates, assert_row_counts]
    failed = []
    for check in checks:
        try:
            check()
        except AssertionError as e:
            log.error(f"QUALITY CHECK FAILED: {e}")
            failed.append(str(e))

    if failed:
        print(f"\n{len(failed)} quality check(s) failed:")
        for f in failed:
            print(f"  - {f}")
        sys.exit(1)

    log.info("All quality checks passed")
    print("All quality checks passed")


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    run()
