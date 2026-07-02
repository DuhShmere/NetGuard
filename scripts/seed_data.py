"""
scripts/seed_data.py
Inserts realistic fake compliance data into PostgreSQL so you can test
the full pipeline (transformer, analytics, anomaly detection, PDF report)
without needing real Cisco or Juniper devices.

Run with:
    python scripts/seed_data.py
"""

import os
import json
import random
import datetime
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://netguard:netguard@localhost/netguard"
)
engine = create_engine(DATABASE_URL)

# ── Fake device definitions ───────────────────────────────────────────────────
DEVICES = [
    {"hostname": "core-sw-01",   "ip": "10.0.0.1",  "vendor": "cisco",   "platform": "nxos"},
    {"hostname": "core-sw-02",   "ip": "10.0.0.2",  "vendor": "cisco",   "platform": "nxos"},
    {"hostname": "edge-rt-01",   "ip": "10.0.1.1",  "vendor": "cisco",   "platform": "ios"},
    {"hostname": "edge-rt-02",   "ip": "10.0.1.2",  "vendor": "cisco",   "platform": "ios"},
    {"hostname": "dist-sw-01",   "ip": "10.0.2.1",  "vendor": "juniper", "platform": "junos"},
    {"hostname": "dist-sw-02",   "ip": "10.0.2.2",  "vendor": "juniper", "platform": "junos"},
    {"hostname": "fw-01",        "ip": "10.0.3.1",  "vendor": "juniper", "platform": "junos"},
    {"hostname": "access-sw-01", "ip": "10.0.4.1",  "vendor": "cisco",   "platform": "ios"},
]

# ── Fake config templates ─────────────────────────────────────────────────────
CISCO_COMPLIANT = """
version 15.4
hostname {hostname}
ip ssh version 2
ip ssh time-out 60
no ip http server
ntp server 10.0.0.100
ntp server 10.0.0.101
snmp-server community netguard-ro RO
snmp-server community netguard-rw RW
line vty 0 15
 transport input ssh
 exec-timeout 10 0
"""

CISCO_NON_COMPLIANT = """
version 15.4
hostname {hostname}
ip http server
snmp-server community public RO
snmp-server community private RW
line vty 0 15
 transport input telnet ssh
"""

JUNIPER_COMPLIANT = """
system {{
    host-name {hostname};
    root-authentication {{
        encrypted-password "$6$abc123";
    }}
    services {{
        ssh {{
            protocol-version v2;
            authentication-order [ publickey password ];
        }}
    }}
    syslog {{
        host 10.0.0.200 {{
            any any;
        }}
    }}
}}
firewall {{
    filter NETGUARD-PROTECT {{
        term ALLOW-SSH {{
            from {{ protocol tcp; destination-port 22; }}
            then accept;
        }}
        term DENY-ALL {{
            then discard;
        }}
    }}
}}
"""

JUNIPER_NON_COMPLIANT = """
system {{
    host-name {hostname};
    services {{
        ssh;
        telnet;
    }}
}}
"""

# ── Violation definitions ─────────────────────────────────────────────────────
CISCO_VIOLATIONS = [
    {"rule_id": "CISCO-001", "severity": "high",   "description": "SSH v2 not enforced"},
    {"rule_id": "CISCO-002", "severity": "high",   "description": "Telnet enabled on VTY lines"},
    {"rule_id": "CISCO-003", "severity": "medium", "description": "No NTP server configured"},
    {"rule_id": "CISCO-004", "severity": "high",   "description": "Default SNMP community string in use"},
]

JUNIPER_VIOLATIONS = [
    {"rule_id": "JNR-001", "severity": "high",   "description": "Root authentication not configured"},
    {"rule_id": "JNR-002", "severity": "medium", "description": "SSH key auth not enforced"},
    {"rule_id": "JNR-003", "severity": "medium", "description": "No syslog server configured"},
    {"rule_id": "JNR-004", "severity": "high",   "description": "No firewall filter defined"},
]


def ensure_schema():
    """Create all tables if they don't exist."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS devices (
                id       SERIAL PRIMARY KEY,
                hostname TEXT UNIQUE NOT NULL,
                ip       TEXT NOT NULL,
                vendor   TEXT NOT NULL,
                platform TEXT,
                port     INTEGER DEFAULT 22
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS raw_snapshots (
                id           SERIAL PRIMARY KEY,
                device_id    INTEGER,
                hostname     TEXT NOT NULL,
                vendor       TEXT NOT NULL,
                raw_config   TEXT NOT NULL,
                collected_at TIMESTAMPTZ DEFAULT NOW(),
                pipeline_run TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stg_compliance (
                id               SERIAL PRIMARY KEY,
                raw_snapshot_id  INTEGER UNIQUE,
                device_id        INTEGER,
                hostname         TEXT NOT NULL,
                vendor           TEXT NOT NULL,
                score            FLOAT NOT NULL,
                violations       JSONB NOT NULL DEFAULT '[]',
                collected_at     TIMESTAMPTZ,
                processed_at     TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.execute(text("""
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
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS analytics_device_daily (
                id           SERIAL PRIMARY KEY,
                report_date  DATE NOT NULL,
                device_id    INTEGER NOT NULL,
                hostname     TEXT NOT NULL,
                vendor       TEXT NOT NULL,
                avg_score    FLOAT,
                min_score    FLOAT,
                violations   INTEGER,
                UNIQUE (report_date, device_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS anomaly_alerts (
                id           SERIAL PRIMARY KEY,
                device_id    INTEGER,
                hostname     TEXT,
                vendor       TEXT,
                alert_type   TEXT,
                detail       JSONB,
                detected_at  TIMESTAMPTZ DEFAULT NOW(),
                acknowledged BOOLEAN DEFAULT FALSE
            )
        """))
        conn.commit()
    print("Schema ready")


def seed_devices():
    """Insert fake devices, skip if already exists."""
    inserted = 0
    with engine.connect() as conn:
        for d in DEVICES:
            existing = conn.execute(
                text("SELECT id FROM devices WHERE hostname = :h"),
                {"h": d["hostname"]}
            ).fetchone()
            if not existing:
                conn.execute(text("""
                    INSERT INTO devices (hostname, ip, vendor, platform, port)
                    VALUES (:hostname, :ip, :vendor, :platform, 22)
                """), d)
                inserted += 1
        conn.commit()
    print(f"Devices: {inserted} inserted, {len(DEVICES) - inserted} already existed")


def get_device_id(conn, hostname):
    row = conn.execute(
        text("SELECT id FROM devices WHERE hostname = :h"),
        {"h": hostname}
    ).fetchone()
    return row[0] if row else None


def make_config(device):
    """Return a realistic fake config string for a device."""
    vendor = device["vendor"]
    # 70% chance of being compliant, 30% non-compliant
    compliant = random.random() > 0.3

    if vendor == "cisco":
        template = CISCO_COMPLIANT if compliant else CISCO_NON_COMPLIANT
    else:
        template = JUNIPER_COMPLIANT if compliant else JUNIPER_NON_COMPLIANT

    return template.format(hostname=device["hostname"]), compliant


def make_violations(device, compliant):
    """Return a list of violations based on vendor and compliance status."""
    if compliant:
        return []
    violations = CISCO_VIOLATIONS if device["vendor"] == "cisco" else JUNIPER_VIOLATIONS
    # Pick 1-3 random violations
    count = random.randint(1, min(3, len(violations)))
    return random.sample(violations, count)


def compute_score(violations):
    deductions = {"high": 20, "medium": 10, "low": 5}
    total = sum(deductions.get(v["severity"], 0) for v in violations)
    return max(0.0, 100.0 - total)


def seed_snapshots(days=14):
    """Insert fake raw snapshots and staged compliance for the past N days."""
    raw_inserted = 0
    stg_inserted = 0

    with engine.connect() as conn:
        for day_offset in range(days, -1, -1):
            snapshot_date = datetime.datetime.now() - datetime.timedelta(days=day_offset)

            for device in DEVICES:
                device_id = get_device_id(conn, device["hostname"])
                if not device_id:
                    continue

                # 2-4 snapshots per device per day
                for _ in range(random.randint(2, 4)):
                    config_text, compliant = make_config(device)
                    collected_at = snapshot_date.replace(
                        hour=random.randint(0, 23),
                        minute=random.randint(0, 59)
                    )

                    # Insert raw snapshot
                    row = conn.execute(text("""
                        INSERT INTO raw_snapshots
                            (device_id, hostname, vendor, raw_config, collected_at)
                        VALUES
                            (:device_id, :hostname, :vendor, :raw_config, :collected_at)
                        RETURNING id
                    """), {
                        "device_id":   device_id,
                        "hostname":    device["hostname"],
                        "vendor":      device["vendor"],
                        "raw_config":  config_text,
                        "collected_at": collected_at,
                    })
                    raw_id = row.fetchone()[0]
                    raw_inserted += 1

                    # Compute compliance
                    violations = make_violations(device, compliant)
                    score = compute_score(violations)

                    # Insert staged compliance
                    conn.execute(text("""
                        INSERT INTO stg_compliance
                            (raw_snapshot_id, device_id, hostname, vendor,
                             score, violations, collected_at)
                        VALUES
                            (:raw_snapshot_id, :device_id, :hostname, :vendor,
                             :score, CAST(:violations AS jsonb), :collected_at)
                        ON CONFLICT (raw_snapshot_id) DO NOTHING
                    """), {
                        "raw_snapshot_id": raw_id,
                        "device_id":       device_id,
                        "hostname":        device["hostname"],
                        "vendor":          device["vendor"],
                        "score":           score,
                        "violations":      json.dumps(violations),
                        "collected_at":    collected_at,
                    })
                    stg_inserted += 1

        conn.commit()

    print(f"Raw snapshots: {raw_inserted} inserted")
    print(f"Staged compliance: {stg_inserted} inserted")


def seed_analytics(days=14):
    """Aggregate staging data into analytics layer."""
    inserted = 0
    with engine.connect() as conn:
        for day_offset in range(days, -1, -1):
            report_date = (datetime.date.today() - datetime.timedelta(days=day_offset))

            # Fleet daily aggregates
            conn.execute(text("""
                INSERT INTO analytics_fleet_daily
                    (report_date, vendor, avg_score, min_score, max_score,
                     device_count, violation_count)
                SELECT
                    DATE(collected_at) AS report_date,
                    vendor,
                    AVG(score),
                    MIN(score),
                    MAX(score),
                    COUNT(DISTINCT device_id),
                    SUM(jsonb_array_length(violations))
                FROM stg_compliance
                WHERE DATE(collected_at) = :report_date
                GROUP BY DATE(collected_at), vendor
                ON CONFLICT (report_date, vendor) DO UPDATE SET
                    avg_score       = EXCLUDED.avg_score,
                    min_score       = EXCLUDED.min_score,
                    max_score       = EXCLUDED.max_score,
                    device_count    = EXCLUDED.device_count,
                    violation_count = EXCLUDED.violation_count
            """), {"report_date": report_date})

            # Device daily aggregates
            conn.execute(text("""
                INSERT INTO analytics_device_daily
                    (report_date, device_id, hostname, vendor,
                     avg_score, min_score, violations)
                SELECT
                    DATE(collected_at),
                    device_id,
                    hostname,
                    vendor,
                    AVG(score),
                    MIN(score),
                    SUM(jsonb_array_length(violations))
                FROM stg_compliance
                WHERE DATE(collected_at) = :report_date
                GROUP BY DATE(collected_at), device_id, hostname, vendor
                ON CONFLICT (report_date, device_id) DO UPDATE SET
                    avg_score  = EXCLUDED.avg_score,
                    min_score  = EXCLUDED.min_score,
                    violations = EXCLUDED.violations
            """), {"report_date": report_date})

            inserted += 1
        conn.commit()

    print(f"Analytics layer: {inserted} days aggregated")


def print_summary():
    """Print a summary of what was seeded."""
    with engine.connect() as conn:
        devices  = conn.execute(text("SELECT COUNT(*) FROM devices")).scalar()
        raw      = conn.execute(text("SELECT COUNT(*) FROM raw_snapshots")).scalar()
        stg      = conn.execute(text("SELECT COUNT(*) FROM stg_compliance")).scalar()
        fleet    = conn.execute(text("SELECT COUNT(*) FROM analytics_fleet_daily")).scalar()
        dev_day  = conn.execute(text("SELECT COUNT(*) FROM analytics_device_daily")).scalar()
        avg_score = conn.execute(text("SELECT ROUND(AVG(score)::numeric, 1) FROM stg_compliance")).scalar()

    print("\n── Seed summary ─────────────────────────────")
    print(f"  Devices:                {devices}")
    print(f"  Raw snapshots:          {raw}")
    print(f"  Staged compliance:      {stg}")
    print(f"  Fleet daily rows:       {fleet}")
    print(f"  Device daily rows:      {dev_day}")
    print(f"  Average compliance score: {avg_score}%")
    print("─────────────────────────────────────────────")
    print("\nNext steps:")
    print("  python -m pipeline.etl.quality")
    print("  python -m pipeline.anomaly.detector")
    print("  python -m pipeline.reports.weekly_report")


if __name__ == "__main__":
    print("Seeding NetGuard database...")
    ensure_schema()
    seed_devices()
    seed_snapshots(days=14)
    seed_analytics(days=14)
    print_summary()
