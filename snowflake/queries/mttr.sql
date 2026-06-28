-- mttr.sql
-- Mean Time To Remediation per rule
-- Measures time between a violation first appearing and it being resolved

WITH violations_timeline AS (
    SELECT
        s.device_id,
        s.hostname,
        violation->>'rule_id' AS rule_id,
        s.collected_at,
        LAG(violation->>'rule_id') OVER (
            PARTITION BY s.device_id, violation->>'rule_id'
            ORDER BY s.collected_at
        ) AS prev_violation,
        LEAD(violation->>'rule_id') OVER (
            PARTITION BY s.device_id, violation->>'rule_id'
            ORDER BY s.collected_at
        ) AS next_violation
    FROM stg_compliance s,
         jsonb_array_elements(s.violations) AS violation
)
SELECT
    rule_id,
    hostname,
    COUNT(*)                                                AS occurrences,
    AVG(EXTRACT(EPOCH FROM (MAX(collected_at) - MIN(collected_at))) / 3600)
                                                            AS avg_hours_open
FROM violations_timeline
GROUP BY rule_id, hostname
ORDER BY avg_hours_open DESC NULLS LAST;
