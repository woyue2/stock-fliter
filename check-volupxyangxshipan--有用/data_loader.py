# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  CSV paths / stock code
# OUTPUT: DataFrames and dicts
# POS:    check-volupxyangxshipan/data_loader.py
# -*- coding: utf-8 -*-
"""
日线数据通过 util/db.get_daily_data() 读取（SQLite 优先，fallback CSV）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from util.db import get_daily_data as _db_get_daily  # noqa: E402
from util.db import get_stock_info_map as _db_get_info_map # noqa: E402

GET_DATA_DIR = PROJECT_ROOT / "get-data"
DATA_DIR = GET_DATA_DIR / "data"
RAW_DIR = Path(os.environ.get("STOCK_RAW_DIR", str(DATA_DIR / "raw")))
OUTPUT_DIR = BASE_DIR / "output"

REQUIRED_COLUMNS = {"date", "open", "high", "low", "close", "volume"}


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def list_raw_files(limit: Optional[int] = None) -> list[Path]:
    files = sorted(RAW_DIR.glob("*.csv"))
    if limit is None:
        return files
    return files[: max(limit, 0)]


def load_stock_info_map() -> dict[str, dict[str, str]]:
    """加载股票元数据：优先 SQLite，fallback CSV。"""
    # 1. 尝试从数据库加载
    db_info = _db_get_info_map()
    if db_info:
        # 统一格式转换，确保 industry 不是 None
        print(f"  [DEBUG] 从 SQLite 加载了 {len(db_info)} 条股票元数据")
        for code in db_info:
            if not db_info[code].get("industry"):
                db_info[code]["industry"] = "未知"
        # 打印几个样本
        samples = ["000407", "600011", "002207"]
        for s in samples:
            if s in db_info:
                print(f"  [DEBUG] 样本 {s}: {db_info[s].get('industry')}")
        return db_info

    # 2. 如果数据库没有，则回退到 CSV
    info_map: dict[str, dict[str, str]] = {}
    paths = [DATA_DIR / "selected_stocks_all.csv", DATA_DIR / "selected_stocks.csv"]
    for path in paths:
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path, dtype=str)
        except Exception:
            continue
        for _, row in df.iterrows():
            code = str(row.get("code", "")).strip().zfill(6)
            if not code:
                continue
            if code not in info_map:
                info_map[code] = {
                    "name": str(row.get("name", "")).strip() or code,
                    "industry": str(row.get("industry", "")).strip() or "未知",
                }
    return info_map


def infer_board(code: str) -> str:
    if code.startswith("688"):
        return "科创板"
    if code.startswith("300") or code.startswith("301"):
        return "创业板"
    if code.startswith("8"):
        return "北交所"
    if code.startswith("002") or code.startswith("000"):
        return "深圳主板"
    if code.startswith("60"):
        return "上海主板"
    return "其他"


def _normalize_code(value: object, fallback: str) -> str:
    text = str(value).strip() if value is not None else ""
    if "." in text:
        text = text.split(".")[-1]
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        return digits.zfill(6)
    return fallback.zfill(6)


def load_stock_df(path: Path) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """从 SQLite（优先）或 CSV（fallback）加载单只股票日线数据。"""
    code = path.stem
    df = _db_get_daily(code)
    if df.empty:
        return None, "数据为空"

    # 补充 code 列（下游需要）
    if "code" not in df.columns:
        df = df.copy()
        df["code"] = code.zfill(6)

    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    df = df.reset_index(drop=True)
    return df, None
