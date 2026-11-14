"""Write README.md from the query outputs, so every number in it is computed.

Re-run after any change:  python src/build_readme.py
Read the generated README once and adjust wording you'd say differently.
"""
import json

import pandas as pd

from config import BASELINE_FRICTION, MAX_BLOCKED_PER_100, RULE_NAMES, ROOT, TABLES_DIR
from economics import best_rule, load_rules, net_saving, summary


def t(name):
    return pd.read_csv(TABLES_DIR / f"{name}.csv")


def num(x):
    a = abs(x)
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            return f"{x / div:,.2f}{suf}"
    return f"{x:,.0f}"


def md_table(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines)


def model_verdict(h2h):
    if not h2h:
        return "was not compared", ""
    gain = h2h["precision_gain_pts"]
    word = ("nothing" if gain <= 0 else "little" if gain < 5
            else "some" if gain < 20 else "a lot on paper")
    detail = (f"At the same recall as {RULE_NAMES[h2h['best_rule']]} ({h2h['rule_recall_pct']:.1f}%), "
              f"the model is {h2h['model_precision_at_same_recall_pct']:.1f}% precise vs the rule's "
              f"{h2h['rule_precision_pct']:.1f}% ({gain:+.1f} points)")
    return word, detail


def main():
    rc = t("01_row_count").to_dict("records")[0]
    by_type = t("02_fraud_by_type")
    fraud_types = by_type[by_type["fraud_rows"] > 0]["type"].tolist()
    fraud_type_share = by_type[by_type["fraud_rows"] > 0]["share_of_all_fraud_pct"].sum()
    signals = t("03_balance_signals").set_index("label")
    flag = t("03_builtin_flag_check").to_dict("records")[0]
    lag = t("03_sender_history_lag").set_index("label")
    chain = t("03_transfer_then_cashout").to_dict("records")[0]
    amount = t("02_fraud_by_amount_bucket")
    top_bucket = amount.loc[amount["fraud_rate_pct"].idxmax()]

    rules = load_rules()
    s = summary(rules)
    best = s["best_rule"]
    b = rules.loc[best]
    up, down = s["switch_up"], s["switch_down"]

    model = json.loads((TABLES_DIR / "07_model_results.json").read_text()) \
        if (TABLES_DIR / "07_model_results.json").exists() else None
    word, detail = model_verdict(model["head_to_head"] if model else None)
    pr = {r["method"]: r["pr_auc"] for r in model["results"] if r["pr_auc"] is not None} if model else {}

    # ------------------------------------------------------------- tables
    rules_view = rules.reset_index()[[
        "rule", "description", "flagged", "true_positives", "false_positives",
        "precision_pct", "recall_pct", "genuine_blocked_per_100", "pct_fraud_value_caught"]]
    rules_view["rule"] = rules_view["rule"].map(RULE_NAMES)
    rules_view["net saving @ baseline"] = [num(v) for v in net_saving(rules, BASELINE_FRICTION)]
    rules_view["guardrail"] = ["fails" if r in s["failing_guardrail"] else "passes" for r in rules.index]
    rules_view.columns = ["Rule", "Logic", "Flagged", "TP", "FP", "Precision %", "Recall %",
                          "Genuine blocked /100", "% fraud value caught", "Net saving @ baseline",
                          "Guardrail"]
    for c in ["Flagged", "TP", "FP"]:
        rules_view[c] = rules_view[c].map(lambda v: f"{v:,}")
    rules_view.to_csv(TABLES_DIR / "rules_comparison.csv", index=False)

    cost = t("06_cost_sensitivity").pivot(index="friction_cost", columns="rule", values="net_saving")
    cost = cost[[r for r in ["Built-in", "A", "B", "C"] if r in cost.columns]]
    cost["Best rule (with guardrail)"] = [RULE_NAMES.get(r, r) for r in
                                          (best_rule(rules, c) for c in cost.index)]
    cost["Best rule (money only)"] = [RULE_NAMES.get(r, r) for r in
                                      (best_rule(rules, c, guardrail=False) for c in cost.index)]
    cost_view = cost.copy()
    for c in cost_view.columns[:-2]:
        cost_view[c] = cost_view[c].map(num)
    cost_view = cost_view.reset_index().rename(columns={"friction_cost": "Friction cost per blocked customer",
                                                        **{k: RULE_NAMES[k] for k in RULE_NAMES}})
    cost_view["Friction cost per blocked customer"] = cost_view["Friction cost per blocked customer"].map(lambda v: f"{v:,}")
    cost_view.to_csv(TABLES_DIR / "cost_sensitivity.csv", index=False)

    model_view = pd.DataFrame(model["results"]) if model else pd.DataFrame()
    if model:
        model_view["pr_auc"] = model_view["pr_auc"].map(lambda v: "-" if pd.isna(v) else f"{v:.3f}")
        model_view.columns = ["Method (test period only)", "PR-AUC", "Precision %", "Recall %"]

    # ------------------------------------------------------ recommendation
    unless = (f"It has the best net saving unless friction cost exceeds **{num(up['friction'])}** per blocked "
              f"customer, where {RULE_NAMES.get(up['to'], up['to'])} takes over"
              if up else "It has the best net saving at every friction cost tested")
    if down:
        unless += (f" (and below **{num(down['friction'])}**, the looser "
                   f"{RULE_NAMES.get(down['from'], down['from'])} wins)")
    guard_note = ""
    if s["best_rule_no_guardrail"] != best:
        guard_note = (f" On money alone {RULE_NAMES.get(s['best_rule_no_guardrail'])} would win, but it blocks "
                      f"{rules.loc[s['best_rule_no_guardrail'], 'genuine_blocked_per_100']:.1f} genuine customers "
                      f"per 100, which fails the {MAX_BLOCKED_PER_100:g}-per-100 guardrail.")
    rec = (f"> **Fraud is confined to {' and '.join(fraud_types)}** ({fraud_type_share:.0f}% of all fraud). "
           f"**{RULE_NAMES[best]}**, which flags *{rules.loc[best, 'description']}*, catches **{b['recall_pct']:.1f}%** of fraud "
           f"and blocks **{b['genuine_blocked_per_100']:.2f} genuine customers per 100**. "
           f"{unless}. The model adds **{word}** on top.{guard_note}")

    drained_f = signals.loc["Fraud", "pct_sender_drained_to_zero"]
    drained_g = signals.loc["Genuine", "pct_sender_drained_to_zero"]
    allbal_f = signals.loc["Fraud", "pct_amount_equals_full_balance"]
    allbal_g = signals.loc["Genuine", "pct_amount_equals_full_balance"]

    readme = f"""# Which fraud rule should a payments product ship?

**A rules-vs-model trade-off on {rc['total_rows']:,} mobile-money transactions, analysed in SQL.**

{rec}

![Rules trade-off](outputs/figures/03_rules_tradeoff.png)

| | |
|---|---|
| **Business question** | Which rule catches the most fraud without blocking genuine customers, and when does that answer change? |
| **Data** | PaySim (Kaggle), {rc['total_rows']:,} **synthetic** transactions over {rc['last_step']} simulated hours |
| **Fraud rate** | {rc['fraud_rate_pct']:.3f}% ({rc['fraud_rows']:,} rows), so accuracy is meaningless and every rule is judged on precision and recall |
| **Stack** | SQLite for all analysis, Python/Pandas for loading and charts, Matplotlib, scikit-learn for the baseline model |

---

## 1. Where fraud concentrates

![Fraud by type](outputs/figures/01_fraud_by_type.png)

- Fraud appears **only in {' and '.join(fraud_types)}**. The other types have zero fraud, so any rule can ignore them.
- **{top_bucket['amount_bucket']}** transactions have the highest fraud rate ({top_bucket['fraud_rate_pct']:.2f}%, vs {rc['fraud_rate_pct']:.3f}% overall).
- The built-in `isFlaggedFraud` rule flagged {flag['flagged_rows']:,} rows and caught **{flag['builtin_recall_pct']:.2f}%** of fraud. It is close to useless.

![Fraud by amount](outputs/figures/02_fraud_by_amount.png)

## 2. Behaviour signals (TRANSFER and CASH_OUT only)

| Signal | Fraud | Genuine |
|---|---|---|
| Sender drained to exactly zero | {drained_f:.1f}% | {drained_g:.1f}% |
| Amount equals sender's entire balance | {allbal_f:.1f}% | {allbal_g:.1f}% |
| Sender balance arithmetic doesn't add up | {signals.loc['Fraud', 'pct_sender_math_broken']:.1f}% | {signals.loc['Genuine', 'pct_sender_math_broken']:.1f}% |
| Receiver balance arithmetic doesn't add up | {signals.loc['Fraud', 'pct_receiver_math_broken']:.1f}% | {signals.loc['Genuine', 'pct_receiver_math_broken']:.1f}% |

- Fraudsters empty the account: that is the strongest, simplest signal and the basis for Rules B and C.
- **Sequence signals don't work here.** Only {lag.loc['Fraud', 'pct_with_prior_txn']:.2f}% of fraud rows have an earlier transaction from the same sender (`LAG` per account), and {chain['pct_followed']:.1f}% of fraud TRANSFERs are followed by a CASH_OUT from the receiving account. PaySim accounts rarely repeat, so "TRANSFER then CASH_OUT" can't be tracked per account.

## 3. Three rules, loose to strict

Each rule is a subset of the one before it ([`sql/04_build_rules.sql`](sql/04_build_rules.sql)), measured with `CASE WHEN` in [`sql/05_measure_rules.sql`](sql/05_measure_rules.sql).

{md_table(rules_view)}

## 4. Cost trade-off

**Assumptions (mine, not data):** a flagged fraud is fully stopped. Each genuine customer blocked costs a flat friction cost (baseline **{BASELINE_FRICTION:,}** currency units). Missed fraud costs the same under every rule, so it drops out.
**Guardrail:** a rule that blocks more than **{MAX_BLOCKED_PER_100:g} genuine customer per 100** is never recommended, however much it saves on paper. {"Fails it: " + ", ".join(RULE_NAMES[r] for r in s["failing_guardrail"]) + "." if s["failing_guardrail"] else "Every rule passes it."}
`net saving = fraud stopped - genuine blocked x friction cost`

![Net saving vs friction](outputs/figures/04_net_saving_vs_friction.png)

{md_table(cost_view)}

{"**Where the answer changes (among rules that pass the guardrail):** " + "; ".join(f"at {num(p['friction'])} the best choice moves from {RULE_NAMES.get(p['from'], p['from'])} to {RULE_NAMES.get(p['to'], p['to'])}" for p in s['all_switches']) + "." if s['all_switches'] else ""}

## 5. Does a model beat the rules?

Logistic regression, `class_weight="balanced"`, TRANSFER and CASH_OUT only, **time-based split** (train on steps 1-{model['split_step'] if model else '?'}, test on later steps: {model['test_rows'] if model else 0:,} rows, {model['test_fraud'] if model else 0:,} fraud). Rules are re-measured on the same test rows.

![Model vs rules](outputs/figures/05_model_vs_rules.png)

{md_table(model_view) if model else "_Run `python src/model.py` to fill this section._"}

- {detail}. **Verdict: the model adds {word} on top of the rule{" - the rule is more precise" if word == "nothing" else ""}.**
- Without balance columns PR-AUC is {pr.get('Model without balance columns', float('nan')):.3f}; with them it is {pr.get('Model with balance columns', float('nan')):.3f}. That jump is the leakage: in PaySim the balance columns almost encode the label.
- For a product team the rule wins on cost of ownership: it is one line of SQL, explainable to support staff and auditors, and needs no retraining.

## Recommendation

1. Ship **{RULE_NAMES[best]}** now. It is cheap to run and easy to explain.
2. Agree the real friction cost with the product and support teams. If it is above {num(up['friction']) if up else 'the tested range'}, switch to {RULE_NAMES.get(up['to'], up['to']) if up else 'a stricter rule'}.
3. Track weekly: fraud caught %, genuine blocked per 100, net saving, and alert volume.
4. Revisit a model only on real data where balances don't leak the label.

## Honest limits

- **The data is synthetic.** PaySim simulates mobile-money behaviour, so these are not real-world fraud findings.
- **The balance columns almost give away the label**, which makes any model look better than it would be in production.
- **Cost figures are my assumptions**, not real data. The sensitivity table shows how the answer moves when they change.
- Accounts rarely repeat in PaySim, so per-customer behaviour (velocity, history) can't be tested.

## Repo structure

```
sql/                  numbered queries, run in order (all core analysis is SQL)
src/load_data.py      CSV -> SQLite in chunks, with indexes
src/run_sql.py        runs sql/*.sql, saves tagged results to outputs/tables/
src/charts.py         the four charts (shared style in src/style.py)
src/model.py          optional baseline model vs rules
src/build_readme.py   writes this README from the outputs, so every number is computed
outputs/tables/       rules_comparison.csv, cost_sensitivity.csv and every query result
outputs/figures/      charts
```

## Reproduce

```bash
pip install -r requirements.txt
# download PS_20174392719_1491204439457_Log.csv from Kaggle (PaySim, by ealaxi) into data/
python run_all.py
```
"""
    (ROOT / "README.md").write_text(readme)
    (TABLES_DIR / "summary.json").write_text(json.dumps({
        "recommendation": rec, "best_rule": best, "fraud_types": fraud_types,
        "best_recall_pct": float(b["recall_pct"]), "best_blocked_per_100": float(b["genuine_blocked_per_100"]),
        "switch_up": up, "switch_down": down, "model_verdict": word, "model_detail": detail, "pr_auc": pr,
    }, indent=2, default=float))
    print("  README.md written")
    print("\n" + rec)


if __name__ == "__main__":
    main()
