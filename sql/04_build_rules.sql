-- =====================================================================
-- 04  BUILD THREE RULES (loose -> strict)
-- Each rule is a subset of the previous one, built from the signals in 03.
--   Rule A  Risky type:      TRANSFER or CASH_OUT
--   Rule B  Drained account: A + sender had money and ends at zero
--   Rule C  Sends it all:    B + amount equals the sender's entire balance
-- The built-in isFlaggedFraud column is kept as a baseline to beat.
-- =====================================================================

DROP VIEW IF EXISTS rule_flags;

CREATE VIEW rule_flags AS
SELECT
    t.*,
    CASE WHEN t.type IN ('TRANSFER', 'CASH_OUT')
         THEN 1 ELSE 0 END                                        AS rule_a,
    CASE WHEN t.type IN ('TRANSFER', 'CASH_OUT')
          AND t.oldbalanceOrg > 0 AND t.newbalanceOrig = 0
         THEN 1 ELSE 0 END                                        AS rule_b,
    CASE WHEN t.type IN ('TRANSFER', 'CASH_OUT')
          AND t.oldbalanceOrg > 0 AND t.newbalanceOrig = 0
          AND ABS(t.amount - t.oldbalanceOrg) < 0.01
         THEN 1 ELSE 0 END                                        AS rule_c,
    t.isFlaggedFraud                                              AS rule_builtin
FROM transactions t;

-- Quick sanity check: how many rows does each rule flag?
-- @save 04_rule_flag_counts
SELECT
    SUM(rule_a)       AS rule_a_flagged,
    SUM(rule_b)       AS rule_b_flagged,
    SUM(rule_c)       AS rule_c_flagged,
    SUM(rule_builtin) AS builtin_flagged
FROM rule_flags;
