# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  file limit
# OUTPUT: DataFrame / sequence
# POS:    check-volratioxturnxpctchg/data_loader.py
# -*- coding: utf-8 -*-
"""
数据加载模块

日线数据通过 util/db.get_daily_data() 读取（SQLite 优先，fallback CSV）。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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
    concepts: str = ""


def load_selected_stocks(path: Path = SELECTED_PATH) -> pd.DataFrame:
    """读取全市场股票清单，并尝试找回 industry 字段"""
    if not path.exists():
        fallback = DATA_DIR / "selected_stocks.csv"
        if fallback.exists():
            df = pd.read_csv(fallback)
        else:
            raise FileNotFoundError(f"找不到股票列表: {path}")
    else:
        df = pd.read_csv(path)

    # 尝试从带有行业数据的备份文件中补充 industry
    copy_path = DATA_DIR / "selected_stocks_all copy.csv"
    if "industry" not in df.columns and copy_path.exists():
        try:
            df_copy = pd.read_csv(copy_path, usecols=["code", "industry"])
            # 清理格式并合并
            df["code_str"] = df["code"].astype(str).str.zfill(6)
            df_copy["code_str"] = df_copy["code"].astype(str).str.zfill(6)
            
            # 使用 left join 合并行业数据
            df = df.merge(df_copy[["code_str", "industry"]], on="code_str", how="left")
            df["industry"] = df["industry"].fillna("未知")
            # 删除临时列
            df = df.drop(columns=["code_str"])
        except Exception:
            df["industry"] = "未知"
    elif "industry" not in df.columns:
        df["industry"] = "未知"
    
    # 同样尝试补全 concepts 字段
    if "concepts" not in df.columns:
        df["concepts"] = ""
        
    return df


def iter_stock_items(limit: int | None = None) -> Iterable[StockItem]:
    """遍历待分析股票项：优先 SQLite，fallback CSV。"""
    # 1. 优先尝试从数据库加载
    db_info = _db_get_info_map()
    if db_info:
        count = 0
        for code, info in db_info.items():
            if limit and count >= limit: break
            yield StockItem(
                code=code,
                name=info.get("name", ""),
                bs_code=info.get("bs_code", ""),
                industry=info.get("industry", "未知") or "未知",
                concepts=info.get("concepts", "")
            )
            count += 1
        return

    # 2. 如果数据库没有，则回退到 CSV
    df = load_selected_stocks()
    if limit:
        df = df.head(limit)
    for row in df.itertuples(index=False):
        yield StockItem(
            code=str(getattr(row, "code")),
            name=str(getattr(row, "name", "")),
            bs_code=str(getattr(row, "bs_code", "")),
            industry=str(getattr(row, "industry", "")),
            concepts=str(getattr(row, "concepts", "")),
        )


def load_daily_data(code: str) -> pd.DataFrame:
    """加载单只股票日线数据（SQLite 优先，fallback CSV）。"""
    return _db_get_daily(code)
