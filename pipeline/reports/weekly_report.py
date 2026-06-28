"""
pipeline/reports/weekly_report.py
Queries the PostgreSQL analytics layer and generates a weekly
compliance PDF report. Saved to reports/ folder which GitHub Actions
uploads as a downloadable artifact.
"""

import os
import datetime
import logging
from sqlalchemy import create_engine, text
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

logging.basicConfig(
    filename=f"logs/anomaly_{datetime.date.today()}.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]
engine       = create_engine(DATABASE_URL)

NAVY   = colors.HexColor("#0C447C")
ACCENT = colors.HexColor("#185FA5")
LIGHT  = colors.HexColor("#E6F1FB")
RED    = colors.HexColor("#A32D2D")
GREEN  = colors.HexColor("#27500A")
RULE   = colors.HexColor("#D3D1C7")
MID    = colors.HexColor("#5F5E5A")
DARK   = colors.HexColor("#2C2C2A")


def get_fleet_summary():
    with engine.connect() as conn:
        return conn.execute(text("""
            SELECT vendor, AVG(avg_score) AS week_avg, MIN(min_score) AS week_min,
                   SUM(violation_count) AS total_violations, MAX(device_count) AS devices
            FROM analytics_fleet_daily
            WHERE report_date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY vendor
            ORDER BY vendor
        """)).mappings().all()


def get_worst_devices():
    with engine.connect() as conn:
        return conn.execute(text("""
            SELECT hostname, vendor, AVG(avg_score) AS week_avg,
                   SUM(violations) AS total_violations
            FROM analytics_device_daily
            WHERE report_date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY hostname, vendor
            ORDER BY week_avg ASC
            LIMIT 10
        """)).mappings().all()


def get_daily_trend():
    with engine.connect() as conn:
        return conn.execute(text("""
            SELECT report_date, AVG(avg_score) AS fleet_avg, SUM(violation_count) AS violations
            FROM analytics_fleet_daily
            WHERE report_date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY report_date
            ORDER BY report_date
        """)).mappings().all()


def get_anomaly_count():
    with engine.connect() as conn:
        return conn.execute(text("""
            SELECT COUNT(*) FROM anomaly_alerts
            WHERE detected_at >= NOW() - INTERVAL '7 days'
        """)).scalar() or 0


def build_pdf(output_path: str):
    doc    = SimpleDocTemplate(output_path, pagesize=letter,
                               leftMargin=0.85*inch, rightMargin=0.85*inch,
                               topMargin=0.85*inch, bottomMargin=0.85*inch)
    styles = getSampleStyleSheet()

    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    title_s  = S("T",  fontName="Helvetica-Bold", fontSize=24, textColor=NAVY,   leading=30)
    sub_s    = S("S",  fontName="Helvetica",       fontSize=11, textColor=MID,    leading=16, spaceAfter=12)
    head_s   = S("H",  fontName="Helvetica-Bold",  fontSize=13, textColor=NAVY,   leading=18, spaceBefore=16, spaceAfter=6)
    body_s   = S("B",  fontName="Helvetica",        fontSize=9.5, textColor=DARK, leading=15)
    small_s  = S("SM", fontName="Helvetica",        fontSize=8,  textColor=MID,   leading=12)

    week_end   = datetime.date.today()
    week_start = week_end - datetime.timedelta(days=7)

    story = []
    story.append(Paragraph("NetGuard", title_s))
    story.append(Paragraph(
        f"Weekly Compliance Report  |  {week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}",
        sub_s))
    story.append(HRFlowable(width="100%", thickness=0.5, color=RULE, spaceAfter=8))

    # Fleet summary table
    story.append(Paragraph("Fleet summary", head_s))
    fleet = get_fleet_summary()
    anomalies = get_anomaly_count()

    summary_data = [
        ["Vendor", "Devices", "7-day avg score", "Min score", "Total violations"],
    ]
    for row in fleet:
        summary_data.append([
            row["vendor"].capitalize(),
            str(int(row["devices"] or 0)),
            f"{float(row['week_avg'] or 0):.1f}%",
            f"{float(row['week_min'] or 0):.1f}%",
            str(int(row["total_violations"] or 0)),
        ])
    summary_data.append(["Anomalies detected", "", str(anomalies), "", ""])

    t = Table(summary_data, colWidths=[1.4*inch, 0.9*inch, 1.5*inch, 1.2*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  LIGHT),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  NAVY),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F7F4")]),
        ("GRID",        (0, 0), (-1, -1), 0.5, RULE),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0,0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # Daily trend table
    story.append(Paragraph("Daily compliance trend", head_s))
    trend = get_daily_trend()
    trend_data = [["Date", "Fleet avg score", "Violations"]]
    for row in trend:
        score = float(row["fleet_avg"] or 0)
        trend_data.append([
            row["report_date"].strftime("%a %b %d") if hasattr(row["report_date"], "strftime") else str(row["report_date"]),
            f"{score:.1f}%",
            str(int(row["violations"] or 0)),
        ])

    t2 = Table(trend_data, colWidths=[2*inch, 2*inch, 2*inch])
    t2.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  LIGHT),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  NAVY),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F7F4")]),
        ("GRID",        (0, 0), (-1, -1), 0.5, RULE),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0,0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t2)
    story.append(Spacer(1, 12))

    # Worst devices
    story.append(Paragraph("Devices needing attention (lowest scores)", head_s))
    worst = get_worst_devices()
    worst_data = [["Hostname", "Vendor", "7-day avg", "Violations"]]
    for row in worst:
        score = float(row["week_avg"] or 0)
        worst_data.append([
            row["hostname"],
            row["vendor"].capitalize(),
            f"{score:.1f}%",
            str(int(row["total_violations"] or 0)),
        ])

    t3 = Table(worst_data, colWidths=[2.2*inch, 1.2*inch, 1.5*inch, 1.4*inch])
    t3.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  LIGHT),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  NAVY),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F7F4")]),
        ("GRID",        (0, 0), (-1, -1), 0.5, RULE),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0,0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t3)
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=RULE))
    story.append(Paragraph(
        f"Generated by NetGuard analytics pipeline  |  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        small_s))

    doc.build(story)
    log.info(f"Report saved to {output_path}")
    print(f"Report saved to {output_path}")


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    date_str = datetime.date.today().strftime("%Y_%m_%d")
    build_pdf(f"reports/netguard_weekly_{date_str}.pdf")
