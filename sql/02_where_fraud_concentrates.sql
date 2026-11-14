-- =====================================================================
-- 02  WHERE FRAUD CONCENTRATES
-- Fraud rate by transaction type, by amount bucket and by hour of day.
-- =====================================================================

-- @save 02_fraud_by_type
SELECT
    type,
    COUNT(*)                                                            AS total_rows,
    SUM(isFraud)                                                        AS fraud_rows,
    ROUND(100.0 * AVG(isFraud), 4)                                      AS fraud_rate_pct,
    ROUND(100.0 * SUM(isFraud) / (SELECT SUM(isFraud) FROM transactions), 2)
                                                                        AS share_of_all_fraud_pct
FROM transactions
GROUP BY type
ORDER BY fraud_rate_pct DESC;

-- @save 02_fraud_by_amount_bucket
WITH bucketed AS (
    SELECT
        isFraud,
        CASE
            WHEN amount <      1000 THEN 1
            WHEN amount <     10000 THEN 2
            WHEN amount <    100000 THEN 3
            WHEN amount <   1000000 THEN 4
            ELSE 5
        END AS bucket_order
    FROM transactions
)
SELECT
    bucket_order,
    CASE bucket_order
        WHEN 1 THEN 'Under 1K'
        WHEN 2 THEN '1K-10K'
        WHEN 3 THEN '10K-100K'
        WHEN 4 THEN '100K-1M'
        ELSE        '1M+'
    END                                                                 AS amount_bucket,
    COUNT(*)                                                            AS total_rows,
    SUM(isFraud)                                                        AS fraud_rows,
    ROUND(100.0 * AVG(isFraud), 4)                                      AS fraud_rate_pct,
    ROUND(100.0 * SUM(isFraud) / (SELECT SUM(isFraud) FROM transactions), 2)
                                                                        AS share_of_all_fraud_pct
FROM bucketed
GROUP BY bucket_order
ORDER BY bucket_order;

-- step is the simulation hour, so step % 24 approximates the hour of day
-- @save 02_fraud_by_hour
SELECT
    step % 24                          AS hour_of_day,
    COUNT(*)                           AS total_rows,
    SUM(isFraud)                       AS fraud_rows,
    ROUND(100.0 * AVG(isFraud), 4)     AS fraud_rate_pct
FROM transactions
GROUP BY hour_of_day
ORDER BY hour_of_day;
