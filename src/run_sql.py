"""Run the numbered SQL files in order and save tagged results as CSV.

A query preceded by a line `-- @save <name>` is written to
outputs/tables/<name>.csv. Untagged statements (e.g. CREATE VIEW) just run.

Usage:  python src/run_sql.py            # all files
        python src/run_sql.py 05         # only files starting with 05
"""
import re
import sqlite3
import sys
import time

import pandas as pd

from config import DB_PATH, SQL_DIR, TABLES_DIR

SAVE_TAG = re.compile(r"^--\s*@save\s+(\S+)", re.MULTILINE)


def split_statements(sql_text):
    buffer = ""
    for line in sql_text.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            yield buffer.strip()
            buffer = ""


def run_file(con, path):
    print(f"\n=== {path.name} ===")
    for stmt in split_statements(path.read_text()):
        tag = SAVE_TAG.search(stmt)
        start = time.time()
        if tag:
            name = tag.group(1)
            df = pd.read_sql_query(stmt, con)
            df.to_csv(TABLES_DIR / f"{name}.csv", index=False)
            print(f"\n-- {name}  ({time.time() - start:.1f}s)")
            with pd.option_context("display.width", 200, "display.max_columns", 20):
                print(df.to_string(index=False, max_rows=30))
        else:
            con.execute(stmt)
    con.commit()


def main(prefix=""):
    if not DB_PATH.exists():
        raise SystemExit("Database missing. Run: python src/load_data.py")
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    for path in sorted(SQL_DIR.glob(f"{prefix}*.sql")):
        run_file(con, path)
    con.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
