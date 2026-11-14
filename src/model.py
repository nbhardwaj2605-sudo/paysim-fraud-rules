"""Step 7 (optional): a baseline logistic regression vs the SQL rules.

- Only TRANSFER and CASH_OUT rows (the only types with fraud).
- Time-based split: earliest 80% of rows (by step) train, the rest test,
  so the model never sees the future.
- class_weight="balanced" because fraud is rare.
- Two models: WITHOUT balance columns, and WITH them. The gap between the
  two shows how much the balance columns leak the label.
- Every rule is re-measured on the same test rows so the comparison is fair.
"""
import json
import sqlite3

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, precision_recall_curve,
                             precision_score, recall_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import style
from config import BASELINE_FRICTION, DB_PATH, FIGURES_DIR, RULE_NAMES, TABLES_DIR
from economics import best_rule, load_rules

QUERY = """
SELECT step, type, amount, oldbalanceOrg, newbalanceOrig, oldbalanceDest,
       newbalanceDest, isFraud, rule_a, rule_b, rule_c, rule_builtin
FROM rule_flags
WHERE type IN ('TRANSFER', 'CASH_OUT')
"""
RULE_COLUMNS = {"A": "rule_a", "B": "rule_b", "C": "rule_c", "Built-in": "rule_builtin"}


def signed_log(x):
    return np.sign(x) * np.log1p(np.abs(x))


def features(df):
    hour = df["step"] % 24
    base = pd.DataFrame({
        "log_amount": np.log1p(df["amount"]),
        "is_transfer": (df["type"] == "TRANSFER").astype(int),
        "hour_sin": np.sin(2 * np.pi * hour / 24),
        "hour_cos": np.cos(2 * np.pi * hour / 24),
    })
    full = base.assign(
        log_old_orig=np.log1p(df["oldbalanceOrg"]),
        log_new_orig=np.log1p(df["newbalanceOrig"]),
        log_old_dest=np.log1p(df["oldbalanceDest"]),
        log_new_dest=np.log1p(df["newbalanceDest"]),
        sender_error=signed_log(df["oldbalanceOrg"] - df["amount"] - df["newbalanceOrig"]),
        receiver_error=signed_log(df["oldbalanceDest"] + df["amount"] - df["newbalanceDest"]),
        drained=((df["oldbalanceOrg"] > 0) & (df["newbalanceOrig"] == 0)).astype(int),
    )
    return base, full


def precision_at_recall(y, scores, target_recall):
    precision, recall, _ = precision_recall_curve(y, scores)
    ok = recall >= target_recall
    return float(precision[ok].max()) if ok.any() else float("nan")


def main():
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(QUERY, con)
    con.close()

    split_step = int(df["step"].quantile(0.8))
    train, test = df["step"] <= split_step, df["step"] > split_step
    y_train, y_test = df.loc[train, "isFraud"], df.loc[test, "isFraud"]
    X_base, X_full = features(df)
    print(f"  train: steps 1-{split_step}, {train.sum():,} rows, {y_train.sum():,} fraud")
    print(f"  test:  steps {split_step + 1}+, {test.sum():,} rows, {y_test.sum():,} fraud")

    results, curves = [], {}
    for name, X in (("Model without balance columns", X_base), ("Model with balance columns", X_full)):
        model = make_pipeline(StandardScaler(),
                              LogisticRegression(class_weight="balanced", max_iter=1000))
        model.fit(X[train], y_train)
        scores = model.predict_proba(X[test])[:, 1]
        pred = (scores >= 0.5).astype(int)
        curves[name] = (y_test.values, scores)
        results.append({
            "method": name,
            "pr_auc": round(average_precision_score(y_test, scores), 4),
            "precision_pct": round(100 * precision_score(y_test, pred, zero_division=0), 2),
            "recall_pct": round(100 * recall_score(y_test, pred, zero_division=0), 2),
        })
        print(f"  {name}: PR-AUC {results[-1]['pr_auc']}")

    for rule, col in RULE_COLUMNS.items():
        pred = df.loc[test, col]
        results.append({
            "method": RULE_NAMES[rule],
            "pr_auc": None,
            "precision_pct": round(100 * precision_score(y_test, pred, zero_division=0), 2),
            "recall_pct": round(100 * recall_score(y_test, pred, zero_division=0), 2),
        })
    pd.DataFrame(results).to_csv(TABLES_DIR / "07_model_vs_rules.csv", index=False)

    # Head-to-head: at the best rule's recall, how precise is the full model?
    best = best_rule(load_rules(), BASELINE_FRICTION)
    head_to_head = None
    if best in RULE_COLUMNS:
        rule_row = next(r for r in results if r["method"] == RULE_NAMES[best])
        y, s = curves["Model with balance columns"]
        model_prec = precision_at_recall(y, s, rule_row["recall_pct"] / 100)
        head_to_head = {
            "best_rule": best,
            "rule_recall_pct": rule_row["recall_pct"],
            "rule_precision_pct": rule_row["precision_pct"],
            "model_precision_at_same_recall_pct": round(100 * model_prec, 2),
            "precision_gain_pts": round(100 * model_prec - rule_row["precision_pct"], 2),
        }
    out = {"split_step": split_step, "test_rows": int(test.sum()),
           "test_fraud": int(y_test.sum()), "results": results, "head_to_head": head_to_head}
    (TABLES_DIR / "07_model_results.json").write_text(json.dumps(out, indent=2))
    pr_chart(curves, results, best)


def pr_chart(curves, results, best):
    fig, ax = style.new()
    for name, (y, s) in curves.items():
        precision, recall, _ = precision_recall_curve(y, s)
        with_bal = "with" in name and "without" not in name
        ax.plot(recall * 100, precision * 100, color=style.MODEL_COLOR if with_bal else style.MUTED,
                ls="-" if with_bal else "--", label=name)
    for rule in RULE_COLUMNS:
        r = next(x for x in results if x["method"] == RULE_NAMES[rule])
        ax.scatter(r["recall_pct"], r["precision_pct"], s=150, color=style.RULE_COLORS[rule],
                   edgecolor=style.SURFACE, linewidth=2, zorder=4)
        near_right = r["recall_pct"] > 80
        ax.annotate(RULE_NAMES[rule], (r["recall_pct"], r["precision_pct"]),
                    xytext=(-10 if near_right else 8, 6), textcoords="offset points",
                    ha="right" if near_right else "left", fontsize=9.5, color=style.TEXT_2)
    ax.set_xlim(0, 105)
    ax.set_ylim(0, 105)
    ax.set_xlabel("Recall: % of fraud caught")
    ax.set_ylabel("Precision: % of flags that are fraud")
    ax.legend(loc="lower left")
    pr = {r["method"]: r["pr_auc"] for r in results if r["pr_auc"] is not None}
    style.finish(
        fig,
        f"Balance columns lift PR-AUC from {pr['Model without balance columns']:.2f} "
        f"to {pr['Model with balance columns']:.2f}, a sign of leakage",
        "Precision-recall on the held-out later time period, with each rule as a point",
        "Source: PaySim synthetic data, TRANSFER and CASH_OUT only. Logistic regression, class_weight='balanced'.",
        FIGURES_DIR / "05_model_vs_rules.png")


if __name__ == "__main__":
    main()
