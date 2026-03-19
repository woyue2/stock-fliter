"""
[L3] sync_missing_to_db.py
[ROLE]: CSV 与 SQLite 之间双向数据对账 (方案 2: 全内存聚合版)
[INPUT]: get-data/data/raw/*.csv, SQLite stocks.db
[OUTPUT]: 同步后的 CSV 并在 DB 中补全缺失行
[POS]: 数据基础设施 / 维护脚本 (高性能版)
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""
import os
import pandas as pd
from pathlib import Path
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from typing import Tuple, List, Optional

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from util.db import upsert_daily_rows, ensure_schema, get_all_daily_fingerprints
except ImportError:
    print("Error: Could not import util.db. Make sure you are running from the project root.")
    sys.exit(1)

# 全局聚合缓冲区
rows_to_insert = []
buffer_lock = threading.Lock()

def scan_csv_and_find_missing(csv_path: Path, db_fingerprints: set):
    """
    [IMPL] 只扫描 CSV，找出数据库中不存在的记录
    """
    code = csv_path.stem.zfill(6)
    added_to_buffer = 0
    try:
        # 极速读取，只解析必要列
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        if df.empty: return 0
        
        df.columns = [c.lower() for c in df.columns]
        # 标准化日期格式
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        df = df.dropna(subset=["date"])

        # 在内存中比对指纹
        missing_rows = []
        for _, row in df.iterrows():
            if (code, row["date"]) not in db_fingerprints:
                record = row.to_dict()
                record["code"] = code
                # 统一字段名
                if "pctchg" not in record and "pctchg" in record: pass
                elif "pctchg" not in record and "pctChg" in record: record["pctchg"] = record.pop("pctChg")
                missing_rows.append(record)
        
        if missing_rows:
            with buffer_lock:
                rows_to_insert.extend(missing_rows)
            added_to_buffer = len(missing_rows)
            
    except Exception as e:
        # 对个别损坏文件报错但不中断
        pass
    return added_to_buffer

def sync_bidirectional(code: str, csv_path: Path) -> Tuple[int, int]:
    """
    [IMPL] 单只股票的双向同步逻辑：CSV 与 DB 互相补全
    Returns: (added_to_db_count, added_to_csv_count)
    """
    added_to_db = 0
    added_to_csv = 0
    code = str(code).zfill(6)
    
    try:
        ensure_schema()
        
        # 1. 读取 CSV
        df_csv = pd.DataFrame()
        if csv_path.exists():
            try:
                df_csv = pd.read_csv(csv_path, encoding="utf-8-sig")
            except Exception:
                df_csv = pd.read_csv(csv_path)
            
            if not df_csv.empty:
                df_csv.columns = [c.lower() for c in df_csv.columns]
                if "date" in df_csv.columns:
                    df_csv["date"] = pd.to_datetime(df_csv["date"], errors="coerce").dt.strftime("%Y-%m-%d")
                    df_csv = df_csv.dropna(subset=["date"])

        # 2. 读取 DB
        from util.db import _connect
        db_rows = []
        with _connect() as conn:
            cursor = conn.execute("SELECT * FROM daily_ohlcv WHERE code = ?", (code,))
            columns = [column[0] for column in cursor.description]
            db_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        df_db = pd.DataFrame(db_rows)
        if not df_db.empty and "date" in df_db.columns:
            df_db["date"] = pd.to_datetime(df_db["date"], errors="coerce").dt.strftime("%Y-%m-%d")

        # 3. CSV -> DB (补全数据库)
        if not df_csv.empty:
            db_dates = set(df_db["date"]) if not df_db.empty else set()
            missing_in_db = []
            for _, row in df_csv.iterrows():
                if row["date"] not in db_dates:
                    record = row.to_dict()
                    record["code"] = code
                    # 统一字段名 (upsert_daily_rows 会处理映射，但这里为了显式安全)
                    if "pctchg" not in record and "pctchg" in record: pass
                    elif "pctchg" not in record and "pctChg" in record: record["pctchg"] = record.pop("pctChg")
                    missing_in_db.append(record)
            
            if missing_in_db:
                upsert_daily_rows(missing_in_db)
                added_to_db = len(missing_in_db)

        # 4. DB -> CSV (补全本地文件)
        if not df_db.empty:
            csv_dates = set(df_csv["date"]) if not df_csv.empty else set()
            missing_in_csv = df_db[~df_db["date"].isin(csv_dates)]
            
            if not missing_in_csv.empty:
                # 只有当确实有数据缺失时才重新写文件
                # 准备 CSV 格式的列名 (尽量保持原始)
                # fetch_daily_history 期望的列名通常是 date,code,open,high,low,close,volume,amount,pctChg,tradestatus,turn
                out_df = pd.concat([df_csv, missing_in_csv], ignore_index=True)
                out_df = out_df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
                
                # 尽量映射回 fetch_daily_history 惯用的列名
                rename_map = {"pctchg": "pctChg"}
                for k, v in rename_map.items():
                    if k in out_df.columns:
                        out_df = out_df.rename(columns={k: v})
                
                out_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                added_to_csv = len(missing_in_csv)

    except Exception as e:
        import logging
        logging.error(f"sync_bidirectional failed for {code}: {e}")
        
    return added_to_db, added_to_csv

def sync_all():
    raw_dir = PROJECT_ROOT / "get-data" / "data" / "raw"
    if not raw_dir.exists():
        print(f"Error: Raw data directory not found at {raw_dir}")
        return

    # 1. 初始化
    ensure_schema()
    
    # 2. 加载 DB 指纹 (方案 2 核心：零查询对账)
    print("🔍 [Step 1/3] 正在加载全量数据库索引 (Memory Fingerprints)...")
    db_fingerprints = get_all_daily_fingerprints()
    print(f"✅ 已加载 {len(db_fingerprints)} 条记录指纹。")

    # 3. 多线程扫描 CSV
    csv_files = list(raw_dir.glob("*.csv"))
    print(f"📂 [Step 2/3] 正在扫描 {len(csv_files)} 个本地 CSV 文件...")
    
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(scan_csv_and_find_missing, p, db_fingerprints): p for p in csv_files}
        for _ in tqdm(as_completed(futures), total=len(csv_files), desc="对账进度"):
            pass

    # 4. 聚合一键入库 (方案 2 核心：单次大事务)
    total_missing = len(rows_to_insert)
    if total_missing > 0:
        print(f"💾 [Step 3/3] 发现 {total_missing} 条缺失记录，正在执行聚合入库 (Single Transaction)...")
        import time
        t_start = time.time()
        # 分批处理防止内存溢出，但使用大 Batch
        batch_size = 50000
        for i in range(0, total_missing, batch_size):
            batch = rows_to_insert[i : i + batch_size]
            upsert_daily_rows(batch)
        print(f"✅ 数据库补全完成！耗时: {time.time()-t_start:.2f}秒")
    else:
        print("✅ 校验完成：所有本地 CSV 数据均已同步至数据库，无需补全。")

if __name__ == "__main__":
    sync_all()
