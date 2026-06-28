-- drift_velocity.sql
-- Rate of compliance score change per device over a rolling 7-day window
-- High negative velocity = device drifting out of compliance fast

SELECT
    d.hostname,
    d.vendor,
    ROUND(CAST(
        REGR_SLOPE(d.avg_score, EXTRACT(EPOCH FROM d.report_date::TIMESTAMPTZ)) AS NUMERIC
    ) * 86400, 4) AS score_change_per_day,
    MIN(d.avg_score)  AS min_score_7d,
    MAX(d.avg_score)  AS max_score_7d,
    AVG(d.avg_score)  AS avg_score_7d
FROM analytics_device_daily d
WHERE d.report_date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY d.hostname, d.vendor
HAVING COUNT(*) >= 3
ORDER BY score_change_per_day ASC;
