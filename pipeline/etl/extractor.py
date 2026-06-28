"""
pipeline/etl/extractor.py
Pulls raw config snapshots from all devices and writes them to the
PostgreSQL raw layer (raw_snapshots table). Triggered by the ingest
GitHub Actions workflow every 15 minutes.
"""

import os
import logging
import datetime
from sqlalchemy import create_engine, text

logging.basicConfig(
    filename=f"logs/ingest_{datetime.date.today()}.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)


def get_all_devices():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, hostname, ip, vendor, platform FROM devices"))
        return result.mappings().all()


def store_raw_snapshot(device_id: int, hostname: str, vendor: str, raw_config: str):
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO raw_snapshots (device_id, hostname, vendor, raw_config, collected_at)
                VALUES (:device_id, :hostname, :vendor, :raw_config, NOW())
            """),
            {"device_id": device_id, "hostname": hostname,
             "vendor": vendor, "raw_config": raw_config},
        )
        conn.commit()


def run():
    devices = get_all_devices()
    log.info(f"Starting ingest for {len(devices)} devices")

    success, failed = 0, 0
    for device in devices:
        try:
            if device["vendor"] == "cisco":
                from cisco.collector import collect_config
                data = collect_config(
                    host=device["ip"],
                    username=os.environ["DEVICE_USERNAME"],
                    password=os.environ["DEVICE_PASSWORD"],
                    platform=device["platform"],
                )
                raw_config = data["running_config"]
            elif device["vendor"] == "juniper":
                from juniper.collector import collect_config
                data = collect_config(
                    host=device["ip"],
                    username=os.environ["DEVICE_USERNAME"],
                    password=os.environ["DEVICE_PASSWORD"],
                )
                raw_config = data["running_config"]
            else:
                log.warning(f"Unknown vendor {device['vendor']} for {device['hostname']}")
                continue

            store_raw_snapshot(device["id"], device["hostname"], device["vendor"], raw_config)
            log.info(f"Ingested {device['hostname']} ({device['vendor']})")
            success += 1

        except Exception as e:
            log.error(f"Failed to ingest {device['hostname']}: {e}")
            failed += 1

    log.info(f"Ingest complete — {success} succeeded, {failed} failed")


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    run()
