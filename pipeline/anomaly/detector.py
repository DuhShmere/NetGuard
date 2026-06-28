"""
pipeline/anomaly/detector.py
Runs Z-score anomaly detection on per-device compliance scores.
Flags devices whose score has dropped unusually fast compared to
their rolling 7-day average. Results written to anomaly_alerts table.
"""

import os
import json
import logging
import datetime
from sqlalchemy import create_engine, text

logging.basicConfig(
    filename=f"logs/anomaly_{datetime.date.today()}.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)

Z_SCORE_THRESHOLD = 2.0   # flag if score drops more than 2 std deviations
MIN_HISTORY_DAYS  = 3     # need at least 3 days of history to detect anomalies


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS anomaly_alerts (
    id           SERIAL PRIMARY KEY,
    device_id    INTEGER,
    hostname     TEXT,
    vendor       TEXT,
    alert_type   TEXT,   -- 'score_drop', 'violation_spike', 'new_violation'
    detail       JSONB,
    detected_at  TIMESTAMPTZ DEFAULT NOW(),
    acknowledged BOOLEAN DEFAULT FALSE
);
"""


def ensure_table():
    with engine.connect() as conn:
        conn.execute(text(SCHEMA_SQL))
        conn.commit()


def get_device_history():
    """Return last 7 days of daily scores per device."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT device_id, hostname, vendor, report_date, avg_score, violations
            FROM analytics_device_daily
            WHERE report_date >= CURRENT_DATE - INTERVAL '7 days'
            ORDER BY device_id, report_date
        """))
        return result.mappings().all()


def compute_z_score(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = variance ** 0.5
    if std == 0:
        return 0.0
    latest = values[-1]
    return (latest - mean) / std


def store_alert(device_id: int, hostname: str, vendor: str,
                alert_type: str, detail: dict):
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO anomaly_alerts (device_id, hostname, vendor, alert_type, detail)
            VALUES (:device_id, :hostname, :vendor, :alert_type, :detail::jsonb)
        """), {
            "device_id": device_id,
            "hostname": hostname,
            "vendor": vendor,
            "alert_type": alert_type,
            "detail": json.dumps(detail),
        })
        conn.commit()


def run():
    ensure_table()
    rows = get_device_history()

    # Group by device
    devices: dict[int, list] = {}
    for row in rows:
        devices.setdefault(row["device_id"], []).append(row)

    alerts_found = 0
    for device_id, history in devices.items():
        history = sorted(history, key=lambda r: r["report_date"])
        if len(history) < MIN_HISTORY_DAYS:
            continue

        hostname = history[-1]["hostname"]
        vendor   = history[-1]["vendor"]
        scores   = [float(r["avg_score"]) for r in history]
        violations = [int(r["violations"]) for r in history]

        # Score drop anomaly
        z = compute_z_score(scores)
        if z < -Z_SCORE_THRESHOLD:
            detail = {
                "z_score": round(z, 2),
                "latest_score": round(scores[-1], 1),
                "7day_avg": round(sum(scores[:-1]) / len(scores[:-1]), 1),
            }
            store_alert(device_id, hostname, vendor, "score_drop", detail)
            log.warning(f"ANOMALY score_drop: {hostname} z={z:.2f} score={scores[-1]:.1f}")
            alerts_found += 1

        # Violation spike anomaly
        vz = compute_z_score([float(v) for v in violations])
        if vz > Z_SCORE_THRESHOLD:
            detail = {
                "z_score": round(vz, 2),
                "latest_violations": violations[-1],
                "7day_avg": round(sum(violations[:-1]) / len(violations[:-1]), 1),
            }
            store_alert(device_id, hostname, vendor, "violation_spike", detail)
            log.warning(f"ANOMALY violation_spike: {hostname} z={vz:.2f} violations={violations[-1]}")
            alerts_found += 1

    log.info(f"Anomaly detection complete — {alerts_found} alerts generated")
    print(f"Anomaly detection complete — {alerts_found} alerts generated")


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    run()
