"""Paths and the labelled cost assumptions used across the project."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CSV_PATH = DATA_DIR / "PS_20174392719_1491204439457_Log.csv"
DB_PATH = DATA_DIR / "paysim.db"
SQL_DIR = ROOT / "sql"
TABLES_DIR = ROOT / "outputs" / "tables"
FIGURES_DIR = ROOT / "outputs" / "figures"

# ---------------------------------------------------------------------------
# ASSUMPTION (not from the data): cost of blocking one genuine transaction,
# in the same currency units as PaySim's `amount`. Must match the comment in
# sql/06_cost_tradeoff.sql. Change it and re-run to see how the answer moves.
# ---------------------------------------------------------------------------
BASELINE_FRICTION = 100

# ---------------------------------------------------------------------------
# ASSUMPTION (product guardrail): a rule may block at most this many genuine
# customers per 100 genuine transactions. A rule that blocks more is never
# recommended, however much money it saves on paper, because no product team
# would ship it. Set to None to turn the guardrail off.
# ---------------------------------------------------------------------------
MAX_BLOCKED_PER_100 = 1.0

RULE_NAMES = {
    "A": "Rule A (risky type)",
    "B": "Rule B (drained account)",
    "C": "Rule C (sends it all)",
    "Built-in": "Built-in flag",
}
