"""
pipeline/anomaly/alerter.py
Reads unacknowledged anomaly alerts and sends Slack webhook messages.
SLACK_WEBHOOK_URL is stored as a GitHub Actions secret.
"""

import os
import json
import logging
import datetime
import urllib.request
from sqlalchemy import create_engine, text

logging.basicConfig(
    filename=f"logs/anomaly_{datetime.date.today()}.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

DATABASE_URL      = os.environ["DATABASE_URL"]
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

engine = create_engine(DATABASE_URL)

ALERT_EMOJI = {
    "score_drop":      ":red_circle:",
    "violation_spike": ":warning:",
    "new_violation":   ":large_yellow_circle:",
}


def get_pending_alerts():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, hostname, vendor, alert_type, detail, detected_at
            FROM anomaly_alerts
            WHERE acknowledged = FALSE
            ORDER BY detected_at DESC
            LIMIT 20
        """))
        return result.mappings().all()


def mark_acknowledged(alert_ids: list[int]):
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE anomaly_alerts SET acknowledged = TRUE WHERE id = ANY(:ids)"),
            {"ids": alert_ids},
        )
        conn.commit()


def send_slack(message: str):
    if not SLACK_WEBHOOK_URL:
        log.info("No Slack webhook configured — skipping notification")
        return
    payload = json.dumps({"text": message}).encode()
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req)


def run():
    alerts = get_pending_alerts()
    if not alerts:
        log.info("No pending alerts")
        return

    lines = [f"*NetGuard — {len(alerts)} anomaly alert(s) detected*\n"]
    ids_to_ack = []

    for alert in alerts:
        detail = alert["detail"] if isinstance(alert["detail"], dict) else json.loads(alert["detail"])
        emoji  = ALERT_EMOJI.get(alert["alert_type"], ":bell:")
        line   = (
            f"{emoji} *{alert['hostname']}* ({alert['vendor']}) — "
            f"`{alert['alert_type']}` | {json.dumps(detail)}"
        )
        lines.append(line)
        ids_to_ack.append(alert["id"])

    message = "\n".join(lines)
    send_slack(message)
    mark_acknowledged(ids_to_ack)
    log.info(f"Sent {len(alerts)} alerts to Slack and marked acknowledged")
    print(f"Sent {len(alerts)} alerts")


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    run()
