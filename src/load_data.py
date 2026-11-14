"""Step 1: load the PaySim CSV into SQLite in chunks, then add indexes.

Usage:  python src/load_data.py [--csv path/to/PS_...csv]
"""
import argparse
import sqlite3
import time

import pandas as pd

from config import CSV_PATH, DB_PATH

SCHEMA = """
CREATE TABLE transactions (
    step            INTEGER,
    type            TEXT,
    amount          REAL,
    nameOrig        TEXT,
    oldbalanceOrg   REAL,
    newbalanceOrig  REAL,
    nameDest        TEXT,
    oldbalanceDest  REAL,
    newbalanceDest  REAL,
    isFraud         INTEGER,
    isFlaggedFraud  INTEGER
)
"""
INDEXED_COLUMNS = ["type", "step", "isFraud", "nameOrig", "nameDest"]
CHUNK_ROWS = 500_000


def main(csv_path=CSV_PATH):
    if not csv_path.exists():
        raise SystemExit(
            f"CSV not found at {csv_path}\n"
            "Download it from Kaggle (PaySim, by ealaxi) and put it in data/."
        )
    DB_PATH.parent.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode = OFF")
    con.execute("PRAGMA synchronous = OFF")
    con.execute(SCHEMA)

    start, loaded = time.time(), 0
    for chunk in pd.read_csv(csv_path, chunksize=CHUNK_ROWS):
        chunk.to_sql("transactions", con, if_exists="append", index=False)
        loaded += len(chunk)
        print(f"  loaded {loaded:>10,} rows  ({time.time() - start:5.0f}s)", flush=True)

    print("  adding indexes ...", flush=True)
    for col in INDEXED_COLUMNS:
        con.execute(f"CREATE INDEX idx_{col} ON transactions({col})")
    con.commit()
    con.close()
    print(f"Done: {loaded:,} rows in {DB_PATH} ({time.time() - start:.0f}s)")


if __name__ == "__main__":
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=CSV_PATH)
    main(parser.parse_args().csv)
