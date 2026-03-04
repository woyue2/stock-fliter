# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  file limit
# OUTPUT: DataFrame / sequence
# POS:    check-tdxmacdxvolume/data_loader.py
# -*- coding: utf-8 -*-
"""
数据加载模块 for check-new-indicators
复用项目统一的数据加载接口
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import pandas as pd
from pandas.errors import ParserError

import os
# 使用项目统一的数据加载路径
BASE_DIR = Path(__file__).resolve().parent
GET_DATA_DIR = BASE_DIR.parent / "get-data"
DATA_DIR = GET_DATA_DIR / "data"
# 新增环境变量支持，加速并行分析时的 I/O
RAW_DIR = Path(os.environ.get("STOCK_RAW_DIR", str(DATA_DIR / "raw")))
SELECTED_PATH = DATA_DIR / "selected_stocks_all.csv"


@dataclass
class StockItem:
    code: str
    name: str
    bs_code: str
    industry: str = ""


def load_selected_stocks(path: Path = SELECTED_PATH) -> pd.DataFrame:
    if not path.exists():
        # 尝试查找其他位置 (兼容性)
        fallback_path = DATA_DIR / "selected_stocks.csv"
        if fallback_path.exists():
            return pd.read_csv(fallback_path)
        raise FileNotFoundError(f"找不到股票列表: {path}")
    df = pd.read_csv(path)
    return df


def iter_stock_items(limit: int | None = None) -> Iterable[StockItem]:
    df = load_selected_stocks()
    if limit:
        df = df.head(limit)
    for row in df.itertuples(index=False):
        code = str(getattr(row, "code"))
        name = str(getattr(row, "name", ""))
        bs_code = str(getattr(row, "bs_code", ""))
        industry = str(getattr(row, "industry", ""))
        yield StockItem(code=code, name=name, bs_code=bs_code, industry=industry)


def load_daily_data(code: str) -> pd.DataFrame:
    # 使用统一的文件命名格式
    path = RAW_DIR / f"{code}.csv"
    if not path.exists():
        return pd.DataFrame()

    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except ParserError:
        try:
            df = pd.read_csv(path)
        except Exception:
            return pd.DataFrame()
            
    if df.empty:
        return pd.DataFrame()

    df.columns = [str(c).lower() for c in df.columns]

    required_cols = {"date", "open", "high", "low", "close", "volume"}
    if not required_cols.issubset(df.columns):
        return pd.DataFrame()

    df = df[list(required_cols)].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    
    # 转换数值列
    numeric_cols = ["open", "high", "low", "close", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        
    return df
