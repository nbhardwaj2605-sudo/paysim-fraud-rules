-- =====================================================================
-- 01  LOAD CHECKS
-- Is the data complete, and how rare is fraud?
-- Lines starting with "-- @save <name>" tell src/run_sql.py to save that
-- query's result to outputs/tables/<name>.csv
-- =====================================================================

-- @save 01_row_count
SELECT
    COUNT(*)                              AS total_rows,
    SUM(isFraud)                          AS fraud_rows,
    ROUND(100.0 * AVG(isFraud), 4)        AS fraud_rate_pct,
    MIN(step)                             AS first_step,
    MAX(step)                             AS last_step,
    COUNT(DISTINCT nameOrig)              AS distinct_senders
FROM transactions;

-- @save 01_null_check
SELECT
    SUM(step IS NULL)            AS step_nulls,
    SUM(type IS NULL)            AS type_nulls,
    SUM(amount IS NULL)          AS amount_nulls,
    SUM(nameOrig IS NULL)        AS nameOrig_nulls,
    SUM(oldbalanceOrg IS NULL)   AS oldbalanceOrg_nulls,
    SUM(newbalanceOrig IS NULL)  AS newbalanceOrig_nulls,
    SUM(nameDest IS NULL)        AS nameDest_nulls,
    SUM(oldbalanceDest IS NULL)  AS oldbalanceDest_nulls,
    SUM(newbalanceDest IS NULL)  AS newbalanceDest_nulls,
    SUM(isFraud IS NULL)         AS isFraud_nulls
FROM transactions;

-- @save 01_type_distribution
SELECT
    type,
    COUNT(*)                                                         AS total_rows,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM transactions), 2) AS pct_of_rows
FROM transactions
GROUP BY type
ORDER BY total_rows DESC;
