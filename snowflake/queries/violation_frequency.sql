-- violation_frequency.sql
-- Which compliance rules fire most often across the fleet

SELECT
    violation->>'rule_id'    AS rule_id,
    violation->>'severity'   AS severity,
    violation->>'description' AS description,
    COUNT(*)                 AS times_fired,
    COUNT(DISTINCT s.device_id) AS devices_affected
FROM stg_compliance s,
     jsonb_array_elements(s.violations) AS violation
WHERE s.collected_at >= NOW() - INTERVAL '7 days'
GROUP BY rule_id, severity, description
ORDER BY times_fired DESC;
