# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  file limit
# OUTPUT: DataFrame / sequence
# POS:    check-volratioxturnxpctchg/data_loader.py
# -*- coding: utf-8 -*-
"""
数据加载模块

复用 get-data/data/raw 的日线数据，额外保留 turn / amount / pctChg 列。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from pandas.errors import ParserError

BASE_DIR = Path(__file__).resolve().parent
GET_DATA_DIR = BASE_DIR.parent / "get-data"
DATA_DIR = GET_DATA_DIR / "data"
RAW_DIR = Path(os.environ.get("STOCK_RAW_DIR", str(DATA_DIR / "raw")))
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
    """逐条迭代股票项"""
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


# ── 需要从 raw CSV 中保留的列 ──────────────────────
_REQUIRED = {"date", "open", "high", "low", "close", "volume"}
_EXTRA = {"amount", "pctchg", "turn"}
_NUMERIC = ["open", "high", "low", "close", "volume", "amount", "pctchg", "turn"]


def load_daily_data(code: str) -> pd.DataFrame:
    """加载单只股票日线数据，包含 turn / amount / pctChg"""
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

    if not _REQUIRED.issubset(df.columns):
        return pd.DataFrame()

    keep = list(_REQUIRED | (_EXTRA & set(df.columns)))
    df = df[keep].copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    for col in _NUMERIC:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df
