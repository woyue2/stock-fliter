# -*- coding: utf-8 -*-
"""
流式日线数据获取工具

提供以下能力:
- 从 selected_stocks_all.csv 读取股票池与行业信息(只读)
- 在不依赖本地 raw/*.csv 的前提下, 按股票代码拉取最近 N 天日 K 数据,
  优先使用 BaoStock, 失败时回退腾讯日 K 接口。

该模块主要为云端轻量 Runner 服务, 尽量减少状态与磁盘依赖。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import importlib

import pandas as pd
import requests

DEFAULT_DAYS = 365


@dataclass
class StockInfo:
    """股票基础信息(从 selected_stocks_all.csv 读取)"""
    code: str
    name: str
    bs_code: str
    industry: str = ""


def _project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).resolve().parent.parent


def _default_selected_path() -> Path:
    """默认股票池文件路径"""
    # 云端精简版: 直接使用 PlanToDeploy 根目录下的 selected_stocks_all.csv
    return _project_root() / "selected_stocks_all.csv"


def load_stock_pool_from_selected_all(
    selected_path: Optional[Path] = None,
    limit: Optional[int] = None,
) -> List[StockInfo]:
    """
    从 selected_stocks_all.csv 加载股票池(只读), 并转换为 StockInfo 列表。

    Args:
        selected_path: 自定义股票池 CSV 路径, 默认使用 get-data/data/selected_stocks_all.csv
        limit: 限制返回的股票数量(用于小样本验证)
    """
    if selected_path is None:
        selected_path = _default_selected_path()

    if not selected_path.exists():
        raise FileNotFoundError(f"找不到股票池文件: {selected_path}")

    df = pd.read_csv(selected_path, dtype=str)
    if limit is not None and limit > 0:
        df = df.head(limit)

    stocks: List[StockInfo] = []
    for _, row in df.iterrows():
        code_raw = str(row.get("code", "")).strip()
        if not code_raw:
            continue
        code = code_raw.zfill(6)

        name = str(row.get("name", "")).strip()

        bs_code = str(row.get("bs_code", "")).strip()
        if not bs_code:
            prefix = "sh" if code.startswith("6") else "sz"
            bs_code = f"{prefix}.{code}"

        industry = str(row.get("industry", "")).strip()
        if industry.lower() == "nan":
            industry = ""

        stocks.append(StockInfo(code=code, name=name, bs_code=bs_code, industry=industry))

    return stocks


_BAOSTOCK_MODULE = None
_BS_LOGGED_IN = False


def get_baostock():
    """懒加载 BaoStock 模块, 不存在时返回 None。"""
    global _BAOSTOCK_MODULE
    if _BAOSTOCK_MODULE is None:
        try:
            _BAOSTOCK_MODULE = importlib.import_module("baostock")
        except Exception:
            return None
    return _BAOSTOCK_MODULE


def login_baostock() -> bool:
    """登录 BaoStock, 失败时返回 False。"""
    global _BS_LOGGED_IN
    if _BS_LOGGED_IN:
        return True

    bs = get_baostock()
    if bs is None:
        return False

    try:
        lg = bs.login()
        if getattr(lg, "error_code", "1") == "0":
            _BS_LOGGED_IN = True
            return True
    except Exception:
        return False
    return False


def logout_baostock() -> None:
    """登出 BaoStock(忽略异常)"""
    global _BS_LOGGED_IN
    if not _BS_LOGGED_IN:
        return

    bs = get_baostock()
    if bs is None:
        return

    try:
        bs.logout()
    except Exception:
        pass
    _BS_LOGGED_IN = False


def _parse_baostock_rows(rows: List[List[str]], fields: List[str]) -> pd.DataFrame:
    """将 BaoStock 返回的原始行转换为标准 OHLCV DataFrame。"""
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=fields)

    # 日期与数值字段转换
    if "date" not in df.columns:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    cols = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in df.columns]
    return df[cols].copy()


def fetch_baostock_daily(
    bs_code: str,
    start_date: str,
    end_date: str,
) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    通过 BaoStock 获取日线数据, 不落盘。

    Returns:
        (DataFrame, 错误信息) —— 成功时错误信息为 None。
    """
    bs = get_baostock()
    if bs is None:
        return pd.DataFrame(), "baostock_not_available"

    try:
        rs = bs.query_history_k_data_plus(
            code=bs_code,
            fields="date,code,open,high,low,close,volume,amount,pctChg,tradestatus",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="2",
        )
    except Exception as exc:
        return pd.DataFrame(), str(exc)

    if getattr(rs, "error_code", "1") != "0":
        return pd.DataFrame(), getattr(rs, "error_msg", "unknown_error")

    rows: List[List[str]] = []
    while rs.next():
        rows.append(rs.get_row_data())

    df = _parse_baostock_rows(rows, rs.fields)
    return df, None


def fetch_tencent_daily(code: str, count: int = DEFAULT_DAYS) -> pd.DataFrame:
    """
    通过腾讯接口获取日线数据, 不落盘。
    """
    prefix = "sh" if str(code).startswith("6") else "sz"
    symbol = f"{prefix}{code}"
    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,{count},qfq"

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    payload = resp.json()

    day_rows = payload.get("data", {}).get(symbol, {}).get("day", [])
    if not day_rows:
        return pd.DataFrame()

    df = pd.DataFrame(day_rows, columns=["date", "open", "close", "high", "low", "volume"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # 统一列顺序
    return df[["date", "open", "high", "low", "close", "volume"]].copy()


def _compute_date_range(days: int, end_date: Optional[str]) -> Tuple[str, str]:
    """根据 days 和 end_date 计算 [start_date, end_date] 区间(字符串形式)。"""
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end_dt = datetime.now().date()

    start_dt = end_dt - timedelta(days=days)
    return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")


def fetch_daily_data_streaming(
    code: str,
    bs_code: str,
    days: int = DEFAULT_DAYS,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    流式获取单只股票最近 N 天日线数据(只在内存中保留)。

    策略:
    - 计算 [start_date, end_date] 区间
    - 如可用, 优先使用 BaoStock; 若失败或无数据, 回退腾讯日 K 接口
    - 返回标准化后的 OHLCV DataFrame, 不做落盘
    """
    start_date, end_date_str = _compute_date_range(days, end_date)

    df = pd.DataFrame()

    # 尝试 BaoStock
    if login_baostock():
        df_bs, err = fetch_baostock_daily(bs_code, start_date, end_date_str)
        if err is None and not df_bs.empty:
            df = df_bs

    # 回退腾讯
    if df.empty:
        try:
            df_tx = fetch_tencent_daily(code, count=days)
        except Exception:
            df_tx = pd.DataFrame()
        df = df_tx

    if df.empty:
        return pd.DataFrame()

    # 再次严格限制时间窗口
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")

    mask = (df["date"] >= start_dt) & (df["date"] <= end_dt)
    df = df.loc[mask].sort_values("date").reset_index(drop=True)

    return df


__all__ = [
    "StockInfo",
    "load_stock_pool_from_selected_all",
    "fetch_daily_data_streaming",
    "login_baostock",
    "logout_baostock",
]
