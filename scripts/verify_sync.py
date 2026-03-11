import sqlite3
import pandas as pd
from pathlib import Path
import sys
import os

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from util.db import _connect
except ImportError:
    print("Error: Could not import util.db. Make sure you are running from the project root.")
    sys.exit(1)

def verify():
    # Check latest date for a few well known stocks
    codes = ['000001', '600000', '300001']
    raw_dir = PROJECT_ROOT / "get-data" / "data" / "raw"

    print("Checking row counts in DB vs CSV:")
    with _connect() as conn:
        for code in codes:
            # Get DB count
            cur = conn.cursor()
            cur.execute("SELECT MAX(date), COUNT(*) FROM daily_ohlcv WHERE code=?", (code,))
            row = cur.fetchone()
            db_date, db_count = row[0], row[1]
            
            # Get CSV count
            csv_path = raw_dir / f"{code}.csv"
            csv_count = 0
            if csv_path.exists():
                try:
                    df = pd.read_csv(csv_path, encoding="utf-8-sig")
                    csv_count = len(df)
                except Exception:
                    pass

            match_str = "✅ Match" if db_count == csv_count else "❌ Mismatch"
            print(f"Code {code}: DB Count = {db_count} | CSV Count = {csv_count} | {match_str} (Latest DB Date: {db_date})")

    print("\nRecent 5 dates across all stocks in DB:")
    with _connect() as conn:
        df = pd.read_sql_query("SELECT date, COUNT(*) as count FROM daily_ohlcv GROUP BY date ORDER BY date DESC LIMIT 5", conn)
        print(df)

if __name__ == "__main__":
    verify()
