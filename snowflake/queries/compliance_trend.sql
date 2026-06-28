-- compliance_trend.sql
-- 7-day rolling average compliance score per vendor
-- Use this for trend line charts on the dashboard

SELECT
    report_date,
    vendor,
    avg_score,
    AVG(avg_score) OVER (
        PARTITION BY vendor
        ORDER BY report_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7day_avg,
    violation_count
FROM analytics_fleet_daily
WHERE report_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY vendor, report_date;
