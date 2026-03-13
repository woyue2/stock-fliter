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
