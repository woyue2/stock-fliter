# [PROTOCOL]: 变更时更新此头部，然后检查父级 /CLAUDE.md
# INPUT:  code: str | rows: list[dict]
# OUTPUT: pd.DataFrame | None
# POS:    util/db.py
# -*- coding: utf-8 -*-
"""
统一数据库访问层 (SQLite)

唯一感知存储后端的地方。所有 check-* 模块通过此接口读写数据，
不直接操作 CSV 或 sqlite3。

数据库路径: get-data/data/stocks.db
表结构:
  - stock_info     (code, name, bs_code, industry, concepts)
  - daily_ohlcv    (code, date, open, high, low, close, volume, amount, pctchg, turn)
"""
from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ── 路径 ──────────────────────────────────────────────────────
_UTIL_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _UTIL_DIR.parent
_DB_PATH = Path(
    os.environ.get(
        "STOCK_DB_PATH",
        str(_PROJECT_ROOT / "get-data" / "data" / "stocks.db"),
    )
)
_RAW_DIR = Path(
    os.environ.get(
        "STOCK_RAW_DIR",
        str(_PROJECT_ROOT / "get-data" / "data" / "raw"),
    )
)
_SELECTED_CSV = _PROJECT_ROOT / "get-data" / "data" / "selected_stocks_all.csv"

# ── DDL ───────────────────────────────────────────────────────
_DDL_STOCK_INFO = """
CREATE TABLE IF NOT EXISTS stock_info (
    code     TEXT PRIMARY KEY,
    name     TEXT NOT NULL DEFAULT '',
    bs_code  TEXT NOT NULL DEFAULT '',
    industry TEXT NOT NULL DEFAULT '未知',
    concepts TEXT NOT NULL DEFAULT ''
)
"""

_DDL_DAILY = """
CREATE TABLE IF NOT EXISTS daily_ohlcv (
    code   TEXT NOT NULL,
    date   TEXT NOT NULL,
    open   REAL,
    high   REAL,
    low    REAL,
    close  REAL,
    volume REAL,
    amount REAL,
    pctchg REAL,
    turn   REAL,
    PRIMARY KEY (code, date)
) WITHOUT ROWID
"""

_DDL_FUND_FLOW = """
CREATE TABLE IF NOT EXISTS daily_fund_flow (
    code     TEXT NOT NULL,
    date     TEXT NOT NULL,
    main_net REAL DEFAULT 0,  -- 主力净额 (10k RMB or Million)
    retail_net REAL DEFAULT 0, -- 散户净额
    PRIMARY KEY (code, date)
) WITHOUT ROWID
"""

_DDL_IDX_DATE = "CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_ohlcv(date)"
_DDL_IDX_FF_DATE = "CREATE INDEX IF NOT EXISTS idx_ff_date ON daily_fund_flow(date)"


# ── 连接管理 ──────────────────────────────────────────────────
def get_db_path() -> Path:
    """返回数据库文件路径（外部可自定义 STOCK_DB_PATH 环境变量）。"""
    return _DB_PATH


def _connect() -> sqlite3.Connection:
    """打开连接并开启 WAL 模式（允许并发读取）。"""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, timeout=30)
    # 极致性能优化
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA mmap_size=2147483648") # 开启 2GB 内存映射，提升大数据量读取性能
    conn.execute("PRAGMA cache_size=-1024000")  # 1GB 缓存
    conn.execute("PRAGMA temp_store=MEMORY")    # 临时表放入内存
    return conn


def ensure_schema() -> None:
    """建表（幂等）。首次调用或数据库不存在时自动执行。"""
    with _connect() as conn:
        conn.execute(_DDL_STOCK_INFO)
        conn.execute(_DDL_DAILY)
        conn.execute(_DDL_FUND_FLOW)
        conn.execute(_DDL_IDX_DATE)
        conn.execute(_DDL_IDX_FF_DATE)
        # 针对 check-zhulistrength 优化的复合索引：代码 + 日期降序 + 核心净额字段
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ff_strength_fast ON daily_fund_flow(code, date DESC, main_net, retail_net)")


# ── 读取 ──────────────────────────────────────────────────────
def get_daily_data(code: str, days: int = 365) -> pd.DataFrame:
    """
    读取单只股票的日线数据。

    优先走 SQLite。若数据库不存在或该股票无记录，自动 fallback 到 CSV。
    返回列：date(datetime), open, high, low, close, volume, amount, pctchg, turn
    """
    if _DB_PATH.exists():
        df = _query_daily_from_db(code, days)
        if not df.empty:
            return df
        logger.debug("db miss for %s, fallback to csv", code)
    return _read_daily_from_csv(code)


def get_stock_info_map() -> dict[str, dict]:
    """
    返回 {code: {name, industry, concepts, bs_code}} 映射。

    优先走 SQLite；fallback 到 selected_stocks_all.csv。
    """
    if _DB_PATH.exists():
        info = _query_stock_info_from_db()
        if info:
            return info
    return _read_stock_info_from_csv()


# ── 写入 ──────────────────────────────────────────────────────
def upsert_daily_rows(rows: list[dict]) -> None:
    """
    批量写入/更新日线数据。

    rows 每项需含键: code, date, open, high, low, close, volume
    可选键: amount, pctchg, turn
    """
    if not rows:
        return
    ensure_schema()
    sql = """
        INSERT OR REPLACE INTO daily_ohlcv
            (code, date, open, high, low, close, volume, amount, pctchg, turn)
        VALUES
            (:code,:date,:open,:high,:low,:close,:volume,
             :amount,:pctchg,:turn)
    """
    normalized = [_normalize_daily_row(r) for r in rows]
    with _connect() as conn:
        conn.executemany(sql, normalized)


def upsert_stock_info(rows: list[dict]) -> None:
    """
    批量写入/更新股票元数据。

    rows 每项需含键: code, name。可选键: bs_code, industry, concepts。
    """
    if not rows:
        return
    ensure_schema()
    sql = """
        INSERT OR REPLACE INTO stock_info
            (code, name, bs_code, industry, concepts)
        VALUES
            (:code, :name, :bs_code, :industry, :concepts)
    """
    normalized = [_normalize_info_row(r) for r in rows]
    with _connect() as conn:
        conn.executemany(sql, normalized)


def upsert_fund_flow_rows(rows: list[dict]) -> None:
    """批量写入/更新资金流向数据。"""
    if not rows:
        return
    ensure_schema()
    sql = """
        INSERT OR REPLACE INTO daily_fund_flow (code, date, main_net, retail_net)
        VALUES (:code, :date, :main_net, :retail_net)
    """
    with _connect() as conn:
        conn.executemany(sql, rows)


def get_fund_flow_data(code: str, days: int = 30) -> pd.DataFrame:
    """读取单只股票或板块的资金流向数据。"""
    if not _DB_PATH.exists():
        return pd.DataFrame()
    try:
        sql = "SELECT date, main_net, retail_net FROM daily_fund_flow WHERE code = ? ORDER BY date ASC"
        with _connect() as conn:
            df = pd.read_sql_query(sql, conn, params=(code,))
        if df.empty:
            return df
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        if days and len(df) > days:
            df = df.iloc[-days:].reset_index(drop=True)
        return df
    except Exception:
        return pd.DataFrame()


# ── 内部实现 ──────────────────────────────────────────────────
def _query_daily_from_db(code: str, days: int) -> pd.DataFrame:
    """从 SQLite 查询，返回标准化 DataFrame（空则返回空 DF）。"""
    try:
        sql = """
            SELECT date, open, high, low, close, volume, amount, pctchg, turn
            FROM   daily_ohlcv
            WHERE  code = ?
            ORDER  BY date ASC
        """
        with _connect() as conn:
            df = pd.read_sql_query(sql, conn, params=(code,))
        if df.empty:
            return df
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).reset_index(drop=True)
        if days and len(df) > days:
            df = df.iloc[-days:].reset_index(drop=True)
        return df
    except Exception:
        logger.error("db query failed for %s", code, exc_info=True)
        return pd.DataFrame()


def _read_daily_from_csv(code: str) -> pd.DataFrame:
    """CSV fallback。读取 raw/{code}.csv，标准化列名后返回。"""
    path = _RAW_DIR / f"{code}.csv"
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        try:
            df = pd.read_csv(path)
        except Exception:
            logger.error("csv read failed: %s", path, exc_info=True)
            return pd.DataFrame()
    if df.empty:
        return df
    df.columns = [c.lower() for c in df.columns]
    required = {"date", "open", "high", "low", "close", "volume"}
    if not required.issubset(df.columns):
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume", "amount", "pctchg", "turn"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _query_stock_info_from_db() -> dict[str, dict]:
    """从 SQLite 读取 stock_info 表，返回 {code: {...}} 字典。"""
    try:
        with _connect() as conn:
            df = pd.read_sql_query("SELECT * FROM stock_info", conn)
        result: dict[str, dict] = {}
        for row in df.itertuples(index=False):
            code_str = str(row.code).zfill(6)
            result[code_str] = {
                "name": str(row.name),
                "bs_code": str(row.bs_code),
                "industry": str(row.industry) if row.industry else "未知",
                "concepts": str(row.concepts) if row.concepts else "",
            }
        return result
    except Exception:
        logger.error("db stock_info query failed", exc_info=True)
        return {}


def _read_stock_info_from_csv() -> dict[str, dict]:
    """CSV fallback：读取 selected_stocks_all.csv，返回 {code: {...}} 字典。"""
    if not _SELECTED_CSV.exists():
        return {}
    try:
        df = pd.read_csv(_SELECTED_CSV, dtype=str)
    except Exception:
        logger.error("csv read failed: %s", _SELECTED_CSV, exc_info=True)
        return {}
    result: dict[str, dict] = {}
    for row in df.itertuples(index=False):
        code = str(getattr(row, "code", "")).zfill(6)
        result[code] = {
            "name": str(getattr(row, "name", "")),
            "bs_code": str(getattr(row, "bs_code", "")),
            "industry": str(getattr(row, "industry", "未知")),
            "concepts": str(getattr(row, "concepts", "")),
        }
    return result


def _normalize_daily_row(r: dict) -> dict:
    """统一 upsert 行的键名和默认值。"""
    return {
        "code":   str(r.get("code", "")),
        "date":   str(r.get("date", "")),
        "open":   _to_float(r.get("open")),
        "high":   _to_float(r.get("high")),
        "low":    _to_float(r.get("low")),
        "close":  _to_float(r.get("close")),
        "volume": _to_float(r.get("volume")),
        "amount": _to_float(r.get("amount")),
        "pctchg": _to_float(r.get("pctchg") or r.get("pctChg")),
        "turn":   _to_float(r.get("turn")),
    }


def _normalize_info_row(r: dict) -> dict:
    """统一 upsert stock_info 行的键名和默认值。"""
    return {
        "code":     str(r.get("code", "")).zfill(6),
        "name":     str(r.get("name", "")),
        "bs_code":  str(r.get("bs_code", "")),
        "industry": str(r.get("industry", "未知")),
        "concepts": str(r.get("concepts", "")),
    }


def _to_float(v: object) -> Optional[float]:
    """安全转 float，失败返回 None。"""
    try:
        return float(v) if v is not None else None  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
