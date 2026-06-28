"""
pipeline/etl/transformer.py
Reads unprocessed rows from raw_snapshots, runs policy checks,
computes compliance scores, and writes to the stg_compliance table.
"""

import os
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


def get_unprocessed_snapshots():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT r.id, r.device_id, r.hostname, r.vendor, r.raw_config, r.collected_at
            FROM raw_snapshots r
            LEFT JOIN stg_compliance s ON s.raw_snapshot_id = r.id
            WHERE s.id IS NULL
            ORDER BY r.collected_at ASC
            LIMIT 500
        """))
        return result.mappings().all()


def compute_score(violations: list) -> float:
    """Score = 100 minus 20 points per high violation, 10 per medium, 5 per low."""
    deductions = {"high": 20, "medium": 10, "low": 5}
    total = sum(deductions.get(v["severity"], 0) for v in violations)
    return max(0.0, 100.0 - total)


def store_staged(raw_snapshot_id: int, device_id: int, hostname: str,
                 vendor: str, score: float, violations: list, collected_at):
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO stg_compliance
                (raw_snapshot_id, device_id, hostname, vendor, score, violations, collected_at)
            VALUES
                (:raw_snapshot_id, :device_id, :hostname, :vendor,
                 :score, :violations::jsonb, :collected_at)
            ON CONFLICT (raw_snapshot_id) DO NOTHING
        """), {
            "raw_snapshot_id": raw_snapshot_id,
            "device_id": device_id,
            "hostname": hostname,
            "vendor": vendor,
            "score": score,
            "violations": __import__("json").dumps(violations),
            "collected_at": collected_at,
        })
        conn.commit()


def run():
    rows = get_unprocessed_snapshots()
    log.info(f"Transforming {len(rows)} unprocessed snapshots")

    for row in rows:
        try:
            if row["vendor"] == "cisco":
                from cisco.policy_checks import run_all_checks
            else:
                from juniper.policy_checks import run_all_checks

            violations = run_all_checks(row["raw_config"])
            score = compute_score(violations)

            store_staged(
                raw_snapshot_id=row["id"],
                device_id=row["device_id"],
                hostname=row["hostname"],
                vendor=row["vendor"],
                score=score,
                violations=violations,
                collected_at=row["collected_at"],
            )
            log.info(f"{row['hostname']} — score {score:.1f}, {len(violations)} violations")

        except Exception as e:
            log.error(f"Failed to transform snapshot {row['id']}: {e}")

    log.info("Transform complete")


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    run()
