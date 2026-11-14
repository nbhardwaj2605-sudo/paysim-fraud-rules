-- =====================================================================
-- 03  BEHAVIOUR SIGNALS
-- Compare fraud vs genuine rows inside TRANSFER and CASH_OUT, the only
-- types where fraud appears (see 02). Each column is a candidate rule signal.
-- =====================================================================

-- @save 03_balance_signals
SELECT
    CASE WHEN isFraud = 1 THEN 'Fraud' ELSE 'Genuine' END                         AS label,
    COUNT(*)                                                                      AS total_rows,
    -- Sender had money and ended at exactly zero
    ROUND(100.0 * AVG(oldbalanceOrg > 0 AND newbalanceOrig = 0), 2)               AS pct_sender_drained_to_zero,
    -- Sender sent their entire balance in one go
    ROUND(100.0 * AVG(oldbalanceOrg > 0 AND ABS(amount - oldbalanceOrg) < 0.01), 2) AS pct_amount_equals_full_balance,
    -- old - amount should equal new on the sender side
    ROUND(100.0 * AVG(ABS(oldbalanceOrg - amount - newbalanceOrig) > 0.01), 2)    AS pct_sender_math_broken,
    -- old + amount should equal new on the receiver side
    ROUND(100.0 * AVG(ABS(oldbalanceDest + amount - newbalanceDest) > 0.01), 2)   AS pct_receiver_math_broken,
    -- Receiver shows zero balance before and after
    ROUND(100.0 * AVG(oldbalanceDest = 0 AND newbalanceDest = 0), 2)              AS pct_receiver_zero_before_after,
    ROUND(AVG(amount), 0)                                                         AS avg_amount
FROM transactions
WHERE type IN ('TRANSFER', 'CASH_OUT')
GROUP BY isFraud
ORDER BY isFraud DESC;

-- How good is the built-in rule flag?
-- @save 03_builtin_flag_check
SELECT
    SUM(isFlaggedFraud)                                         AS flagged_rows,
    SUM(isFlaggedFraud * isFraud)                               AS flagged_and_fraud,
    SUM(isFraud)                                                AS total_fraud,
    ROUND(100.0 * SUM(isFlaggedFraud * isFraud) / SUM(isFraud), 3) AS builtin_recall_pct
FROM transactions;

-- Do senders have a transaction history? LAG gives each sender's previous
-- transaction type. If almost nobody has one, per-account sequence rules
-- (e.g. TRANSFER then CASH_OUT from the same account) cannot work here.
-- @save 03_sender_history_lag
WITH seq AS (
    SELECT
        isFraud,
        LAG(type) OVER (PARTITION BY nameOrig ORDER BY step) AS prev_type
    FROM transactions
    WHERE type IN ('TRANSFER', 'CASH_OUT')
)
SELECT
    CASE WHEN isFraud = 1 THEN 'Fraud' ELSE 'Genuine' END        AS label,
    COUNT(*)                                                     AS total_rows,
    SUM(prev_type IS NOT NULL)                                   AS rows_with_prior_txn,
    ROUND(100.0 * AVG(prev_type IS NOT NULL), 3)                 AS pct_with_prior_txn
FROM seq
GROUP BY isFraud
ORDER BY isFraud DESC;

-- Is a fraud TRANSFER followed by a CASH_OUT from the receiving account?
-- @save 03_transfer_then_cashout
SELECT
    COUNT(*)                                                     AS fraud_transfers,
    SUM(EXISTS (
        SELECT 1 FROM transactions c
        WHERE c.nameOrig = t.nameDest
          AND c.type = 'CASH_OUT'
          AND c.step >= t.step
    ))                                                           AS followed_by_cashout_from_receiver,
    ROUND(100.0 * AVG(EXISTS (
        SELECT 1 FROM transactions c
        WHERE c.nameOrig = t.nameDest
          AND c.type = 'CASH_OUT'
          AND c.step >= t.step
    )), 2)                                                       AS pct_followed
FROM transactions t
WHERE t.type = 'TRANSFER' AND t.isFraud = 1;
