# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  CSV paths
# OUTPUT: DataFrames and dicts
# POS:    check-volupxyangxshipan/data_loader.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

import os
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
GET_DATA_DIR = PROJECT_ROOT / "get-data"
DATA_DIR = GET_DATA_DIR / "data"
# 新增环境变量支持，加速并行分析时的 I/O
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
    fallback_code = path.stem
    try:
        df = pd.read_csv(path)
    except Exception:
        return None, "文件读取失败"

    if df.empty:
        return None, "空文件"

    columns = {c.strip(): c for c in df.columns}
    missing = [col for col in REQUIRED_COLUMNS if col not in columns]
    if missing:
        return None, "缺少关键列"

    try:
        work = pd.DataFrame()
        work["date"] = pd.to_datetime(df[columns["date"]], errors="coerce")
        work["open"] = pd.to_numeric(df[columns["open"]], errors="coerce")
        work["high"] = pd.to_numeric(df[columns["high"]], errors="coerce")
        work["low"] = pd.to_numeric(df[columns["low"]], errors="coerce")
        work["close"] = pd.to_numeric(df[columns["close"]], errors="coerce")
        work["volume"] = pd.to_numeric(df[columns["volume"]], errors="coerce")
        if "code" in columns:
            work["code"] = df[columns["code"]].map(lambda v: _normalize_code(v, fallback_code))
        else:
            work["code"] = fallback_code.zfill(6)
    except Exception:
        return None, "字段转换失败"

    work = work.dropna(subset=["date"]).copy()
    if work.empty:
        return None, "日期不可解析"

    work = work.sort_values("date")
    work = work.drop_duplicates(subset=["date"], keep="last")
    work = work.reset_index(drop=True)
    return work, None
