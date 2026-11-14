-- =====================================================================
-- 05  MEASURE EACH RULE
-- Confusion counts with CASE WHEN, then precision, recall and
-- genuine customers blocked per 100 genuine transactions.
-- Accuracy is left out on purpose: with ~0.13% fraud, a rule that flags
-- nothing is 99.87% "accurate".
-- =====================================================================

-- @save 05_rules_comparison
WITH totals AS (
    SELECT
        SUM(isFraud)          AS total_fraud,
        SUM(1 - isFraud)      AS total_genuine,
        SUM(amount * isFraud) AS total_fraud_amount
    FROM rule_flags
),
counts AS (
    SELECT 'Built-in' AS rule, 'isFlaggedFraud column (baseline)' AS description,
           SUM(rule_builtin) AS flagged,
           SUM(CASE WHEN rule_builtin = 1 AND isFraud = 1 THEN 1 ELSE 0 END)      AS tp,
           SUM(CASE WHEN rule_builtin = 1 AND isFraud = 0 THEN 1 ELSE 0 END)      AS fp,
           SUM(CASE WHEN rule_builtin = 1 AND isFraud = 1 THEN amount ELSE 0 END) AS caught_amount
    FROM rule_flags
    UNION ALL
    SELECT 'A', 'TRANSFER or CASH_OUT',
           SUM(rule_a),
           SUM(CASE WHEN rule_a = 1 AND isFraud = 1 THEN 1 ELSE 0 END),
           SUM(CASE WHEN rule_a = 1 AND isFraud = 0 THEN 1 ELSE 0 END),
           SUM(CASE WHEN rule_a = 1 AND isFraud = 1 THEN amount ELSE 0 END)
    FROM rule_flags
    UNION ALL
    SELECT 'B', 'A + sender balance drained to zero',
           SUM(rule_b),
           SUM(CASE WHEN rule_b = 1 AND isFraud = 1 THEN 1 ELSE 0 END),
           SUM(CASE WHEN rule_b = 1 AND isFraud = 0 THEN 1 ELSE 0 END),
           SUM(CASE WHEN rule_b = 1 AND isFraud = 1 THEN amount ELSE 0 END)
    FROM rule_flags
    UNION ALL
    SELECT 'C', 'B + amount equals entire balance',
           SUM(rule_c),
           SUM(CASE WHEN rule_c = 1 AND isFraud = 1 THEN 1 ELSE 0 END),
           SUM(CASE WHEN rule_c = 1 AND isFraud = 0 THEN 1 ELSE 0 END),
           SUM(CASE WHEN rule_c = 1 AND isFraud = 1 THEN amount ELSE 0 END)
    FROM rule_flags
)
SELECT
    c.rule,
    c.description,
    c.flagged,
    c.tp                                                    AS true_positives,
    c.fp                                                    AS false_positives,
    t.total_fraud - c.tp                                    AS false_negatives,
    ROUND(100.0 * c.tp / NULLIF(c.flagged, 0), 2)           AS precision_pct,
    ROUND(100.0 * c.tp / t.total_fraud, 2)                  AS recall_pct,
    ROUND(100.0 * c.fp / t.total_genuine, 3)                AS genuine_blocked_per_100,
    ROUND(c.caught_amount, 0)                               AS fraud_amount_caught,
    ROUND(100.0 * c.caught_amount / t.total_fraud_amount, 2) AS pct_fraud_value_caught
FROM counts c CROSS JOIN totals t;
