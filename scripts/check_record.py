import sqlite3
import pandas as pd
from pathlib import Path
import sys

PROJECT_ROOT = Path("/mnt/f/QIANQIAN/stock-fliter")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from util.db import _connect

def check_data():
    with _connect() as conn:
        df = pd.read_sql_query("SELECT * FROM daily_ohlcv WHERE code='000001' AND date='2026-03-11'", conn)
        print("Record for 000001 on 2026-03-11:")
        print(df.to_dict('records'))

if __name__ == "__main__":
    check_data()
