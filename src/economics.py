"""Net-saving maths on top of the SQL rule results (sql/05, sql/06).

net saving(rule, c) = fraud loss avoided - genuine blocked x c
where c is the friction cost per blocked genuine transaction (an assumption).

Only rules that pass the customer-experience guardrail
(MAX_BLOCKED_PER_100 in config.py) can be recommended.
"""
import pandas as pd

from config import BASELINE_FRICTION, MAX_BLOCKED_PER_100, TABLES_DIR

NO_RULE = "No rule"


def load_rules():
    return pd.read_csv(TABLES_DIR / "05_rules_comparison.csv").set_index("rule")


def passes_guardrail(rules):
    if MAX_BLOCKED_PER_100 is None:
        return pd.Series(True, index=rules.index)
    return rules["genuine_blocked_per_100"] <= MAX_BLOCKED_PER_100


def eligible(rules):
    ok = rules[passes_guardrail(rules)]
    return ok if len(ok) else rules


def net_saving(rules, friction):
    return rules["fraud_amount_caught"] - rules["false_positives"] * friction


def best_rule(rules, friction, guardrail=True):
    pool = eligible(rules) if guardrail else rules
    net = net_saving(pool, friction)
    return net.idxmax() if net.max() > 0 else NO_RULE


def switch_points(rules, guardrail=True):
    """Exact friction costs at which the best rule changes.

    Two rules tie where their net-saving lines cross:
    c* = (saved_i - saved_j) / (blocked_i - blocked_j). A rule ties with
    "no rule" (net 0) at c* = saved_i / blocked_i.
    """
    pool = eligible(rules) if guardrail else rules
    saved, blocked = pool["fraud_amount_caught"], pool["false_positives"]
    candidates = set()
    for i in pool.index:
        if blocked[i] > 0:
            candidates.add(saved[i] / blocked[i])
        for j in pool.index:
            if blocked[i] != blocked[j]:
                c = (saved[i] - saved[j]) / (blocked[i] - blocked[j])
                if c > 0:
                    candidates.add(c)
    points = []
    for c in sorted(candidates):
        before = best_rule(pool, c * (1 - 1e-9), guardrail=False)
        after = best_rule(pool, c * (1 + 1e-9), guardrail=False)
        if before != after:
            points.append({"friction": float(c), "from": before, "to": after})
    return points


def summary(rules=None, baseline=BASELINE_FRICTION):
    rules = load_rules() if rules is None else rules
    points = switch_points(rules)
    above = [p for p in points if p["friction"] > baseline]
    below = [p for p in points if p["friction"] < baseline]
    ok = passes_guardrail(rules)
    return {
        "baseline_friction": baseline,
        "guardrail": MAX_BLOCKED_PER_100,
        "best_rule": best_rule(rules, baseline),
        "best_rule_no_guardrail": best_rule(rules, baseline, guardrail=False),
        "failing_guardrail": [r for r in rules.index if not ok[r]],
        "switch_up": above[0] if above else None,      # best changes if friction rises past this
        "switch_down": below[-1] if below else None,   # best changes if friction falls below this
        "all_switches": points,
    }
