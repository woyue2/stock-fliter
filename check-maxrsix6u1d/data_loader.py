# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  file limit / seed 
# OUTPUT: DataFrame / sequence
# POS:    check-maxrsix6u1d/data_loader.py
# -*- coding: utf-8 -*-
"""
数据加载模块（复用 just-stock-down 的完整数据）
日线数据通过 util/db.get_daily_data() 读取（SQLite 优先，fallback CSV）。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = BASE_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from util.db import get_daily_data as _db_get_daily  # noqa: E402
from util.db import get_stock_info_map as _db_get_info_map # noqa: E402

GET_DATA_DIR = BASE_DIR.parent / "get-data"
DATA_DIR = GET_DATA_DIR / "data"
SELECTED_PATH = DATA_DIR / "selected_stocks_all.csv"


@dataclass
class StockItem:
    code: str
    name: str
    bs_code: str
    industry: str = ""


def load_selected_stocks(path: Path = SELECTED_PATH) -> pd.DataFrame:
    if not path.exists():
        # Fallback to older filename if new one doesn't exist
        fallback_path = DATA_DIR / "selected_stocks.csv"
        if fallback_path.exists():
            return pd.read_csv(fallback_path)
        raise FileNotFoundError(f"找不到股票列表: {path}")
    df = pd.read_csv(path)
    return df


def iter_stock_items(limit: int | None = None) -> Iterable[StockItem]:
    """遍历待分析股票项：优先 SQLite，fallback CSV。"""
    # 1. 尝试从数据库加载
    db_info = _db_get_info_map()
    if db_info:
        count = 0
        for code, info in db_info.items():
            if limit and count >= limit: break
            yield StockItem(
                code=code,
                name=info.get("name", ""),
                bs_code=info.get("bs_code", ""),
                industry=info.get("industry", "未知") or "未知"
            )
            count += 1
        return

    # 2. 如果数据库没有，则回退到 CSV
    df = load_selected_stocks()
    if limit:
        df = df.head(limit)
    for row in df.itertuples(index=False):
        code = str(getattr(row, "code"))
        name = str(getattr(row, "name", ""))
        bs_code = str(getattr(row, "bs_code", ""))
        industry = str(getattr(row, "industry", ""))
        yield StockItem(code=code, name=name, bs_code=bs_code, industry=industry)


def sample_stock_items(sample_size: int, seed: int = 42) -> List[StockItem]:
    """随机采样股票：优先 SQLite，fallback CSV。"""
    import random
    db_info = _db_get_info_map()
    if db_info:
        codes = list(db_info.keys())
        random.seed(seed)
        sampled_codes = random.sample(codes, min(sample_size, len(codes)))
        items: List[StockItem] = []
        for code in sampled_codes:
            info = db_info[code]
            items.append(
                StockItem(
                    code=code,
                    name=info.get("name", ""),
                    bs_code=info.get("bs_code", ""),
                    industry=info.get("industry", "未知") or "未知"
                )
            )
        return items

    # CSV fallback
    df = load_selected_stocks()
    sampled = df.sample(n=sample_size, random_state=seed)
    items: List[StockItem] = []
    for row in sampled.itertuples(index=False):
        items.append(
            StockItem(
                code=str(getattr(row, "code")),
                name=str(getattr(row, "name", "")),
                bs_code=str(getattr(row, "bs_code", "")),
                industry=str(getattr(row, "industry", "")),
            )
        )
    return items


def load_daily_data(code: str) -> pd.DataFrame:
    """加载单只股票日线数据（SQLite 优先，fallback CSV）。"""
    return _db_get_daily(code)
