import os
import pandas as pd
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from util.db import upsert_daily_rows, _connect
except ImportError:
    print("Error: Could not import util.db. Make sure you are running from the project root.")
    sys.exit(1)

def get_db_df(code: str) -> pd.DataFrame:
    with _connect() as conn:
        query = "SELECT date, open, high, low, close, volume, amount, pctchg, turn FROM daily_ohlcv WHERE code=?"
        df = pd.read_sql_query(query, conn, params=(code,))
    return df

def sync_bidirectional(code: str, csv_path: Path) -> tuple[int, int]:
    """
    Syncs data bidirectionally between CSV and DB for a given stock code.
    Returns a tuple of (rows_added_to_db, rows_added_to_csv).
    """
    try:
        if csv_path.exists():
            csv_df = pd.read_csv(csv_path, encoding="utf-8-sig")
            if not csv_df.empty:
                csv_df.columns = [c.lower() for c in csv_df.columns]
                # Ensure date is string format YYYY-MM-DD
                csv_df["date"] = pd.to_datetime(csv_df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
                csv_df = csv_df.dropna(subset=["date"])
            else:
                csv_df = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "amount", "pctchg", "turn"])
        else:
            csv_df = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "amount", "pctchg", "turn"])
        
        db_df = get_db_df(code)
        
        if not db_df.empty:
            db_df["date"] = pd.to_datetime(db_df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
            db_df = db_df.dropna(subset=["date"])
        else:
            db_df = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "amount", "pctchg", "turn"])

        # Compare dates
        csv_dates = set(csv_df["date"].tolist()) if not csv_df.empty else set()
        db_dates = set(db_df["date"].tolist()) if not db_df.empty else set()

        missing_in_db = csv_dates - db_dates
        missing_in_csv = db_dates - csv_dates

        rows_added_to_db = 0
        rows_added_to_csv = 0

        # Sync CSV -> DB
        if missing_in_db and not csv_df.empty:
            sync_to_db_df = csv_df[csv_df["date"].isin(missing_in_db)].copy()
            sync_to_db_df["code"] = code
            records = sync_to_db_df.to_dict(orient="records")
            # We can upsert missing only
            upsert_daily_rows(records)
            rows_added_to_db = len(records)

        # Sync DB -> CSV
        if missing_in_csv and not db_df.empty:
            sync_to_csv_df = db_df[db_df["date"].isin(missing_in_csv)].copy()
            # If CSV was completely empty but path exists, or if we need to merge
            if csv_df.empty:
                merged_csv = sync_to_csv_df
            else:
                merged_csv = pd.concat([csv_df, sync_to_csv_df], ignore_index=True)
            
            # Additional safety: append 'source' and 'tradestatus' cols if merging
            if "code" not in merged_csv.columns:
                merged_csv["code"] = code
            if "source" not in merged_csv.columns:
                merged_csv["source"] = "db_sync"
            if "tradestatus" not in merged_csv.columns:
                merged_csv["tradestatus"] = 1

            merged_csv["date_dt"] = pd.to_datetime(merged_csv["date"])
            merged_csv = merged_csv.sort_values("date_dt").drop(columns=["date_dt"], errors="ignore") if "date_dt" in merged_csv.columns else merged_csv
            
            merged_csv = merged_csv.drop_duplicates(subset=["date"], keep="last")
            
            # Format order
            cols = ["date", "code", "open", "high", "low", "close", "volume", "amount", "pctchg", "tradestatus", "turn", "source"]
            # Ensure all columns exist
            for c in cols:
                if c not in merged_csv.columns:
                    if c == "code": merged_csv["code"] = code
                    elif c == "tradestatus": merged_csv["tradestatus"] = 1
                    elif c == "source": merged_csv["source"] = "db_sync"
                    elif c == "pctchg" and "pctChg" in merged_csv.columns: 
                        merged_csv = merged_csv.rename(columns={"pctChg": "pctchg"})
                    else: merged_csv[c] = None
                    
            # Rename pctchg to pctChg for CSV consistency based on 000001.csv examples
            if "pctchg" in merged_csv.columns:
                merged_csv = merged_csv.rename(columns={"pctchg": "pctChg"})

            csv_cols_order = ["date", "code", "open", "high", "low", "close", "volume", "amount", "pctChg", "tradestatus", "turn", "source"]
            # Retain any extra columns by appending instead of strict filtering, but prioritize order
            final_cols = [c for c in csv_cols_order if c in merged_csv.columns] + [c for c in merged_csv.columns if c not in csv_cols_order]
            merged_csv = merged_csv[final_cols]
            
            merged_csv.to_csv(csv_path, index=False, encoding="utf-8-sig")
            rows_added_to_csv = len(missing_in_csv)

        return rows_added_to_db, rows_added_to_csv
    except Exception as e:
        print(f"Error processing {code}: {e}")
        return 0, 0

def sync_all():
    raw_dir = PROJECT_ROOT / "get-data" / "data" / "raw"
    if not raw_dir.exists():
        print(f"Error: Raw data directory not found at {raw_dir}")
        return

    csv_files = list(raw_dir.glob("*.csv"))
    total_files = len(csv_files)
    print(f"Found {total_files} CSV files to process.")

    total_added_db = 0
    total_added_csv = 0

    def process_file(csv_path):
        code = csv_path.stem.zfill(6)
        return sync_bidirectional(code, csv_path)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_file, p): p for p in csv_files}
        for future in tqdm(as_completed(futures), total=total_files, desc="Syncing"):
            added_db, added_csv = future.result()
            total_added_db += added_db
            total_added_csv += added_csv

    print(f"Sync complete. Added {total_added_db} missed rows to DB, {total_added_csv} missed rows to CSVs.")

if __name__ == "__main__":
    sync_all()
