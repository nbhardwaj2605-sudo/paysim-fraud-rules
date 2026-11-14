-- =====================================================================
-- 06  COST TRADE-OFF
--
-- ASSUMPTIONS (mine, not from the data - change them and re-run):
--   A1. A flagged fraud transaction is fully stopped, so its whole amount
--       counts as fraud loss avoided.
--   A2. Every genuine transaction that gets blocked costs a flat
--       FRICTION COST (support contact, abandoned payment, churn risk).
--   A3. Baseline friction cost = 100 currency units per blocked genuine
--       transaction (set in src/config.py as BASELINE_FRICTION).
--   A4. Fraud the rule misses costs its full amount. That cost is the same
--       starting point for every rule, so it drops out of the comparison.
--   A5. Guardrail: a rule that blocks more than 1 genuine customer per 100
--       is never recommended (MAX_BLOCKED_PER_100 in src/config.py).
--
--   net saving = fraud loss avoided - (genuine blocked x friction cost)
--
-- The friction cost is varied below to find where the best rule changes.
-- =====================================================================

-- @save 06_cost_sensitivity
WITH friction(friction_cost) AS (
    VALUES (1), (10), (100), (1000), (10000), (100000)
),
rule_value AS (
    SELECT 'Built-in' AS rule,
           SUM(CASE WHEN rule_builtin = 1 AND isFraud = 1 THEN amount ELSE 0 END) AS loss_avoided,
           SUM(CASE WHEN rule_builtin = 1 AND isFraud = 0 THEN 1 ELSE 0 END)      AS genuine_blocked
    FROM rule_flags
    UNION ALL
    SELECT 'A',
           SUM(CASE WHEN rule_a = 1 AND isFraud = 1 THEN amount ELSE 0 END),
           SUM(CASE WHEN rule_a = 1 AND isFraud = 0 THEN 1 ELSE 0 END)
    FROM rule_flags
    UNION ALL
    SELECT 'B',
           SUM(CASE WHEN rule_b = 1 AND isFraud = 1 THEN amount ELSE 0 END),
           SUM(CASE WHEN rule_b = 1 AND isFraud = 0 THEN 1 ELSE 0 END)
    FROM rule_flags
    UNION ALL
    SELECT 'C',
           SUM(CASE WHEN rule_c = 1 AND isFraud = 1 THEN amount ELSE 0 END),
           SUM(CASE WHEN rule_c = 1 AND isFraud = 0 THEN 1 ELSE 0 END)
    FROM rule_flags
)
SELECT
    f.friction_cost,
    r.rule,
    ROUND(r.loss_avoided, 0)                                   AS fraud_loss_avoided,
    r.genuine_blocked,
    r.genuine_blocked * f.friction_cost                        AS friction_cost_total,
    ROUND(r.loss_avoided - r.genuine_blocked * f.friction_cost, 0) AS net_saving
FROM friction f CROSS JOIN rule_value r
ORDER BY f.friction_cost, r.rule;
