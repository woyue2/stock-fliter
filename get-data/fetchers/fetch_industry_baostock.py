# -*- coding: utf-8 -*-
"""
[L3] fetch_industry_baostock.py
[ROLE]: 更新股票列表行业信息 (BaoStock 版)
[INPUT]: data/selected_stocks_all.csv
[OUTPUT]: data/selected_stocks_all.csv, SQLite stocks.db
[PROTOCOL]: 变更时更新此头部，然后检查 L2/CLAUDE.md

更新股票列表信息（行业、板块等）
"""
import sys
import pandas as pd
from pathlib import Path
import baostock as bs
import time
from tqdm import tqdm

# 添加项目根目录到路径以导入 util
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from util.db import upsert_stock_info
except ImportError:
    def upsert_stock_info(rows): pass

DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "selected_stocks_all.csv"

def login_baostock():
    lg = bs.login()
    if lg.error_code != '0':
        print(f"login respond error_code:{lg.error_code}")
        print(f"login respond  error_msg:{lg.error_msg}")
        return False
    return True

def logout_baostock():
    bs.logout()

def get_stock_industry(code):
    try:
        rs = bs.query_stock_industry(code=code)
        if rs.error_code == '0' and rs.next():
            row = rs.get_row_data()
            if len(row) >= 4:
                return row[3] # industry
    except Exception:
        pass
    return ""

def main():
    import argparse
    parser = argparse.ArgumentParser(description="股票行业信息更新工具")
    parser.add_argument("--force", action="store_true", help="强制全量更新（默认仅更新缺失项）")
    args = parser.parse_args()

    if not CSV_PATH.exists():
        print(f"Error: {CSV_PATH} not found.")
        return

    print(f"Reading {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH, dtype=str)
    
    if "bs_code" not in df.columns:
        df["bs_code"] = df["code"].apply(lambda x: f"sh.{x}" if str(x).startswith("6") else f"sz.{x}")

    # 1. 确定需要抓取的清单
    if "industry" not in df.columns:
        df["industry"] = ""
    
    if args.force:
        to_check_mask = pd.Series([True] * len(df))
    else:
        # 只抓取 industry 为空、NaN 或 "未知" 的
        to_check_mask = df["industry"].isna() | (df["industry"] == "") | (df["industry"] == "未知")
    
    subset = df[to_check_mask]
    if subset.empty:
        print("🎉 所有股票行业信息均已存在，无需更新。如需强制刷新请加 --force")
        return

    print(f"需要更新 {len(subset)} / {len(df)} 只股票的行业信息...")

    print("Logging in to BaoStock...")
    if not login_baostock():
        return

    print("Fetching industry info...")
    indices = subset.index.tolist()
    
    # 增量记录，用于后续同步 SQLite
    new_data_for_db = []

    pbar = tqdm(indices, desc="进度", unit="只")
    for idx in pbar:
        row = df.loc[idx]
        code = str(row["code"]).zfill(6)
        bs_code = row["bs_code"]
        ind = get_stock_industry(bs_code)
        
        df.at[idx, "industry"] = ind
        pbar.set_postfix_str(f"Code: {code} -> {ind}")
        
        # 准备同步 SQLite 的数据
        new_data_for_db.append({
            "code": code,
            "name": row.get("name", ""),
            "industry": ind,
            "concepts": row.get("concepts", "")
        })

        # 每 100 只同步一次 SQLite，防止意外中断
        if len(new_data_for_db) >= 100:
            upsert_stock_info(new_data_for_db)
            new_data_for_db = []

    print("Logging out...")
    logout_baostock()

    if new_data_for_db:
        upsert_stock_info(new_data_for_db)

    # 2. 保存 CSV
    print(f"Saving to {CSV_PATH}...")
    try:
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    except PermissionError:
        print(f"[WARN] 无法更新 CSV: {CSV_PATH}，文件可能被 Windows 程序占用。")

    # 3. 同步至 SQLite (全量同步确保一致性)
    print("Synchronizing to SQLite...")
    try:
        # 构造全量数据
        all_data_for_db = []
        for _, r in df.iterrows():
            all_data_for_db.append({
                "code": str(r["code"]).zfill(6),
                "name": r.get("name", ""),
                "industry": r.get("industry", ""),
                "concepts": r.get("concepts", "")
            })
        upsert_stock_info(all_data_for_db)
        print(f"Done. SQLite synced {len(all_data_for_db)} stocks.")
    except Exception as e:
        print(f"Failed to sync SQLite: {e}")

if __name__ == "__main__":
    main()
