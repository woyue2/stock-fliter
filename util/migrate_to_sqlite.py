# [PROTOCOL]: 变更时更新此头部，然后检查父级 /CLAUDE.md
# INPUT:  get-data/data/raw/*.csv + selected_stocks_all.csv
# OUTPUT: get-data/data/stocks.db
# POS:    util/migrate_to_sqlite.py
# -*- coding: utf-8 -*-
"""
一次性迁移工具：将 CSV 数据导入 SQLite 数据库。

使用方法:
  python util/migrate_to_sqlite.py              # 全量迁移
  python util/migrate_to_sqlite.py --test 10    # 只迁移前10只股票（测试）
  python util/migrate_to_sqlite.py --info-only  # 只迁移股票元数据
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd
from tqdm import tqdm

# 把项目根目录加入路径
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from util.db import ensure_schema, get_db_path, upsert_daily_rows, upsert_stock_info

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_RAW_DIR = _ROOT / "get-data" / "data" / "raw"
_SELECTED_CSV = _ROOT / "get-data" / "data" / "selected_stocks_all.csv"

# 每次批量写入的行数（控制内存）
_BATCH_SIZE = 5000


def migrate_stock_info() -> int:
    """迁移 selected_stocks_all.csv → stock_info 表，返回写入行数。"""
    if not _SELECTED_CSV.exists():
        logger.error("找不到 %s", _SELECTED_CSV)
        return 0
    df = pd.read_csv(_SELECTED_CSV, dtype=str)
    rows = df.to_dict("records")
    upsert_stock_info(rows)
    logger.info("stock_info: 写入 %d 条", len(rows))
    return len(rows)


def migrate_one_stock(csv_path: Path) -> int:
    """读取单只股票的 CSV，返回写入行数。失败返回 0。"""
    code = csv_path.stem
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
    except Exception:
        try:
            df = pd.read_csv(csv_path)
        except Exception:
            return 0

    if df.empty:
        return 0

    df.columns = [c.lower() for c in df.columns]
    required = {"date", "open", "high", "low", "close", "volume"}
    if not required.issubset(df.columns):
        return 0

    df["code"] = code
    rows = df.to_dict("records")

    # 分批写入，避免单次 executemany 过大
    for i in range(0, len(rows), _BATCH_SIZE):
        upsert_daily_rows(rows[i: i + _BATCH_SIZE])

    return len(rows)


def get_existing_codes() -> set[str]:
    """获取数据库中已存在日线数据的股票代码。"""
    import sqlite3
    from util.db import get_db_path
    db_path = get_db_path()
    if not db_path.exists():
        return set()
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT DISTINCT code FROM daily_ohlcv")
            return {r[0] for r in cursor.fetchall()}
    except Exception:
        return set()


def migrate_all_daily(limit: int | None = None, force: bool = False) -> tuple[int, int]:
    """
    迁移所有 raw/*.csv → daily_ohlcv 表。
    
    Args:
        limit: 限制处理只数
        force: 是否强制覆盖已存在的数据（默认跳过）
    """
    files = sorted(_RAW_DIR.glob("*.csv"))
    if limit:
        files = files[:limit]

    # 增量逻辑：获取已存在的代码
    existing_codes = set() if force else get_existing_codes()
    if existing_codes:
        logger.info(f"检测到数据库中已有 {len(existing_codes)} 只股票的数据，将执行增量迁移...")

    total_rows = 0
    success = 0
    skipped = 0
    t0 = time.time()

    # 使用 tqdm 进度条
    pbar = tqdm(files, desc="迁移进度", unit="只")
    for csv_path in pbar:
        code = csv_path.stem
        if code in existing_codes:
            skipped += 1
            continue
        
        n = migrate_one_stock(csv_path)
        if n > 0:
            success += 1
            total_rows += n
            # 在进度条右侧显示当前处理的代码
            pbar.set_postfix_str(f"Code: {code}")

    elapsed = time.time() - t0
    print(f"\n" + "─" * 40)
    logger.info(
        "日线迁移完成: %d 成功, %d 跳过, 共 %d 行, 耗时 %.1fs",
        success, skipped, total_rows, elapsed,
    )
    return success, total_rows


def verify(limit: int = 5) -> None:
    """
    验证：从 DB 中已存在的股票里随机抽样，对比 CSV 与 SQLite 行数一致性。
    """
    import random
    import sqlite3
    from util.db import get_db_path

    db_path = get_db_path()
    if not db_path.exists():
        print("  ❌ 数据库不存在，请先运行迁移")
        return

    # 从 DB 中取已迁移的 code 列表
    with sqlite3.connect(db_path) as conn:
        codes_in_db = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT code FROM daily_ohlcv"
            ).fetchall()
        ]

    if not codes_in_db:
        print("  ⚠️ daily_ohlcv 表为空，迁移可能未成功")
        return

    print(f"\n正在从数据库 {len(codes_in_db)} 只股票中随机抽取 {limit} 只进行行数核对...")
    sample_codes = random.sample(codes_in_db, min(limit, len(codes_in_db)))
    ok = 0
    for code in sample_codes:
        csv_path = _RAW_DIR / f"{code}.csv"
        try:
            csv_rows = len(pd.read_csv(csv_path)) if csv_path.exists() else -1
            with sqlite3.connect(db_path) as conn:
                db_rows = conn.execute(
                    "SELECT COUNT(*) FROM daily_ohlcv WHERE code=?", (code,)
                ).fetchone()[0]
            match = "✅" if csv_rows == db_rows else "⚠️"
            if csv_rows == db_rows:
                ok += 1
            print(f"  {match} {code}: CSV={csv_rows}, DB={db_rows}")
        except Exception as e:
            print(f"  ❌ {code}: {e}")

    print(f"\n验证结果: {ok}/{len(sample_codes)} 抽样一致")


def main() -> int:
    parser = argparse.ArgumentParser(description="CSV → SQLite 增量迁移工具")
    parser.add_argument("--test", type=int, metavar="N", help="只处理前 N 只股票")
    parser.add_argument("--force", action="store_true", help="强制覆盖已有的数据（默认增量跳过）")
    parser.add_argument("--info-only", action="store_true", help="只更新股票元数据 (stock_info)")
    parser.add_argument("--verify", type=int, metavar="N", default=5, help="迁移后随机验证 N 只股票")
    args = parser.parse_args()

    db_path = get_db_path()
    print(f"🚀 数据库地址: {db_path}")
    print(f"📂 原始数据: {_RAW_DIR}")
    print(f"📋 股票清单: {_SELECTED_CSV}")
    print("-" * 40)

    ensure_schema()
    
    # 1. 元数据始终同步
    migrate_stock_info()

    # 2. 日线增量迁移
    if not args.info_only:
        migrate_all_daily(limit=args.test, force=args.force)

    # 3. 验证
    if args.verify > 0:
        print("\n" + "─" * 40)
        verify(limit=args.verify)

    print(f"\n✅ 全部完成！数据库位置: {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
