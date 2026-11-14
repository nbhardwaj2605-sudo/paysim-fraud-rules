"""Run the whole project end to end.

    python run_all.py              # load (if needed), SQL, model, charts, README
    python run_all.py --reload     # force a fresh CSV -> SQLite load
    python run_all.py --skip-model # skip the optional model (saves ~2-5 min)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import build_readme  # noqa: E402
import charts  # noqa: E402
import load_data  # noqa: E402
import model  # noqa: E402
import run_sql  # noqa: E402
from config import DB_PATH, FIGURES_DIR, TABLES_DIR  # noqa: E402


def main():
    args = set(sys.argv[1:])
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    if "--reload" in args or not DB_PATH.exists():
        print("\n[1/5] Loading CSV into SQLite")
        load_data.main()
    print("\n[2/5] Running SQL")
    run_sql.main()
    if "--skip-model" not in args:
        print("\n[3/5] Training baseline model")
        model.main()
    print("\n[4/5] Drawing charts")
    charts.main()
    print("\n[5/5] Writing README")
    build_readme.main()


if __name__ == "__main__":
    main()
