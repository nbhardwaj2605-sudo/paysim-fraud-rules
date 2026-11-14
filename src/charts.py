"""Step 8: the four headline charts, built from the CSVs the SQL produced."""
import matplotlib.ticker
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

import style
from config import BASELINE_FRICTION, FIGURES_DIR, MAX_BLOCKED_PER_100, RULE_NAMES, TABLES_DIR
from economics import load_rules, net_saving, summary


def short_number(x, _pos=None):
    a = abs(x)
    for div, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            return f"{x / div:,.1f}{suffix}".replace(".0" + suffix, suffix)
    return f"{x:,.0f}"


def source_line():
    n = int(pd.read_csv(TABLES_DIR / "01_row_count.csv").loc[0, "total_rows"])
    return f"Source: PaySim synthetic mobile-money data (Kaggle), {n:,} transactions. Synthetic data, not real customers."


# ---------------------------------------------------------------- 1. by type
def fraud_by_type():
    d = pd.read_csv(TABLES_DIR / "02_fraud_by_type.csv").sort_values("fraud_rate_pct")
    has_fraud = d["fraud_rows"] > 0
    fraud_types = d.loc[has_fraud].sort_values("fraud_rate_pct", ascending=False)["type"].tolist()

    fig, ax = style.new(left=0.14)
    colors = [style.HIGHLIGHT if f else style.OTHER for f in has_fraud]
    bars = ax.barh(d["type"], d["fraud_rate_pct"], color=colors, height=0.62)
    xmax = d["fraud_rate_pct"].max()
    for bar, rate, n_fraud in zip(bars, d["fraud_rate_pct"], d["fraud_rows"]):
        label = f"{rate:.2f}%   ({n_fraud:,} fraud rows)" if n_fraud else "0 fraud rows"
        ax.text(bar.get_width() + xmax * 0.015, bar.get_y() + bar.get_height() / 2, label,
                va="center", fontsize=10.5,
                color=style.TEXT if n_fraud else style.MUTED)
    ax.set_xlim(0, xmax * 1.45)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1f}%"))
    ax.set_xlabel("Share of transactions that are fraud")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0, labelsize=11)

    others = len(d) - len(fraud_types)
    title = (f"Fraud happens only in {' and '.join(fraud_types)}"
             if others else "Fraud rate by transaction type")
    style.finish(fig, title,
                 f"Fraud rate by transaction type. The other {others} types have no fraud at all.",
                 source_line(), FIGURES_DIR / "01_fraud_by_type.png")


# ------------------------------------------------------ 2. by amount bucket
def fraud_by_amount():
    d = pd.read_csv(TABLES_DIR / "02_fraud_by_amount_bucket.csv").sort_values("bucket_order")
    overall = pd.read_csv(TABLES_DIR / "01_row_count.csv").loc[0, "fraud_rate_pct"]
    top = d.loc[d["fraud_rate_pct"].idxmax()]

    fig, ax = style.new()
    colors = [style.HIGHLIGHT if b == top["amount_bucket"] else style.OTHER for b in d["amount_bucket"]]
    bars = ax.bar(d["amount_bucket"], d["fraud_rate_pct"], color=colors, width=0.62)
    ymax = d["fraud_rate_pct"].max()
    for bar, rate, share in zip(bars, d["fraud_rate_pct"], d["share_of_all_fraud_pct"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + ymax * 0.02,
                f"{rate:.2f}%\n{share:.0f}% of all fraud", ha="center", va="bottom", fontsize=10)
    ax.axhline(overall, color=style.MUTED, lw=1, ls="--")
    ax.text(len(d) - 0.5, overall + ymax * 0.02, f"Overall rate {overall:.2f}%",
            ha="right", va="bottom", fontsize=9.5, color=style.TEXT_2)
    ax.set_ylim(0, ymax * 1.3)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1f}%"))
    ax.set_ylabel("Share of transactions that are fraud")
    ax.set_xlabel("Transaction amount (currency units)")
    ax.grid(axis="x", visible=False)

    ratio = top["fraud_rate_pct"] / overall if overall else float("nan")
    style.finish(fig,
                 f"{top['amount_bucket']} transactions are {ratio:.0f}x riskier than average",
                 "Fraud rate by amount bucket, with each bucket's share of all fraud",
                 source_line(), FIGURES_DIR / "02_fraud_by_amount.png")


# ------------------------------------------------------- 3. rules trade-off
def rules_tradeoff():
    rules = load_rules()
    best = summary(rules)["best_rule"]
    xmax = rules["genuine_blocked_per_100"].max()

    fig, ax = style.new()
    ax.set_xscale("symlog", linthresh=0.1, linscale=0.6)
    right_edge = max(xmax * 3, 10)
    if MAX_BLOCKED_PER_100 is not None:
        ax.axvspan(MAX_BLOCKED_PER_100, right_edge, color=style.GRID, alpha=0.5, zorder=0, lw=0)
        ax.text(MAX_BLOCKED_PER_100 * 1.15, -5,
                f"Fails guardrail: blocks more than {MAX_BLOCKED_PER_100:g} genuine customer per 100",
                fontsize=9, color=style.TEXT_2, va="bottom")
    # Rules far to the right get labels to their left, alternating below/above so they never collide
    crowded = rules[rules["genuine_blocked_per_100"] > 1].sort_values("genuine_blocked_per_100", ascending=False)
    placement = {r: ("left", "below" if i % 2 == 0 else "above") for i, r in enumerate(crowded.index)}
    for rule, row in rules.iterrows():
        is_best = rule == best
        x, y = row["genuine_blocked_per_100"], row["recall_pct"]
        ax.scatter(x, y, s=280 if is_best else 150, color=style.RULE_COLORS[rule],
                   edgecolor=style.SURFACE, linewidth=2, zorder=3)
        label = (f"{RULE_NAMES[rule]}{'  - recommended' if is_best else ''}\n"
                 f"{y:.1f}% caught, {x:.2f} blocked per 100")
        side, vert = placement.get(rule, ("right", "below"))
        ax.annotate(label, (x, y),
                    xytext=(-14 if side == "left" else 14, -8 if vert == "below" else 10),
                    textcoords="offset points",
                    ha="right" if side == "left" else "left",
                    va="top" if vert == "below" else "bottom", fontsize=10,
                    fontweight="bold" if is_best else "normal",
                    color=style.TEXT if is_best else style.TEXT_2)
    ax.set_xlim(-0.02, right_edge)
    ticks = [t for t in (0, 0.1, 0.5, 1, 5, 10, 50, 100) if t <= right_edge]
    ax.set_xticks(ticks)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.set_ylim(-8, 112)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_xlabel("Genuine customers blocked per 100 genuine transactions (lower is better, symlog scale)")
    ax.set_ylabel("Fraud caught, recall (higher is better)")

    b = rules.loc[best] if best in rules.index else None
    title = (f"{RULE_NAMES[best]} catches {b['recall_pct']:.0f}% of fraud, "
             f"blocking {b['genuine_blocked_per_100']:.2f} per 100"
             if b is not None else "Fraud caught vs genuine customers blocked")
    style.finish(fig, title,
                 "Each rule's trade-off between catching fraud and blocking genuine customers (top-left is ideal)",
                 source_line(), FIGURES_DIR / "03_rules_tradeoff.png")


# ------------------------------------------- 4. net saving vs friction cost
def net_saving_vs_friction():
    rules = load_rules()
    s = summary(rules)
    top = max(1e5, s['switch_up']['friction'] * 4 if s['switch_up'] else 0)
    grid = np.geomspace(1, top, 600)

    fig, ax = style.new()
    curves = {r: np.array([net_saving(rules, c)[r] for c in grid]) for r in rules.index}
    peak = max(c.max() for c in curves.values())
    for rule, y in curves.items():
        is_best = rule == s["best_rule"]
        fails = rule in s["failing_guardrail"]
        ax.plot(grid, y, color=style.RULE_COLORS[rule], lw=3 if is_best else 2,
                ls=":" if fails else "-", alpha=0.6 if fails else 1,
                label=RULE_NAMES[rule] + ("  (fails guardrail)" if fails else ""),
                zorder=3 if is_best else 2)
    ax.axhline(0, color=style.MUTED, lw=1)
    ax.axvline(BASELINE_FRICTION, color=style.TEXT_2, lw=1, ls=":")
    ax.text(BASELINE_FRICTION * 1.08, peak * 1.12, f"Baseline assumption\n{BASELINE_FRICTION:,} per blocked customer",
            fontsize=9, color=style.TEXT_2, va="top")
    if s["switch_up"]:
        w = s["switch_up"]
        ax.axvline(w["friction"], color=style.TEXT, lw=1.2, ls="--")
        to_name = RULE_NAMES.get(w["to"], w["to"])
        ax.text(w["friction"] / 1.1, -peak * 0.08,
                f"Above {short_number(w['friction'])},\n{to_name}\nbecomes the better choice",
                fontsize=9, color=style.TEXT, va="top", ha="right")
    ax.set_xscale("log")
    ax.set_ylim(-peak * 0.6, peak * 1.18)
    ax.yaxis.set_major_formatter(FuncFormatter(short_number))
    ax.xaxis.set_major_formatter(FuncFormatter(short_number))
    ax.set_xlabel("Assumed friction cost per blocked genuine transaction (log scale)")
    ax.set_ylabel("Net saving = fraud stopped - friction cost")
    ax.legend(loc="lower left")

    best = RULE_NAMES.get(s["best_rule"], s["best_rule"])
    if s["switch_up"]:
        title = f"{best} wins until friction passes {short_number(s['switch_up']['friction'])} per customer"
    else:
        title = f"{best} wins across every friction cost tested"
    style.finish(fig, title,
                 "Net saving of each rule as the cost of blocking a genuine customer rises (assumption, not data)",
                 source_line(), FIGURES_DIR / "04_net_saving_vs_friction.png")


def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fraud_by_type()
    fraud_by_amount()
    rules_tradeoff()
    net_saving_vs_friction()


if __name__ == "__main__":
    main()
