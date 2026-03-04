# -*- coding: utf-8 -*-
"""
数据加载模块（复用 just-stock-down 的完整数据）
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import pandas as pd
from pandas.errors import ParserError


BASE_DIR = Path(__file__).resolve().parent
GET_DATA_DIR = BASE_DIR.parent / "get-data"
DATA_DIR = GET_DATA_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
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
    path = RAW_DIR / f"{code}.csv"
    if not path.exists():
        return pd.DataFrame()

    try:
        df = pd.read_csv(path)
    except ParserError:
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
    return df
