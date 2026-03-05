# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  pd.DataFrame (日线 ≥ 6 行), dict{code, name, industry}, dict (config)
# OUTPUT: dict (命中结果) | None (未命中)
# POS:    check-volratioxturnxpctchg/analyzers/surge_analyzer.py
# -*- coding: utf-8 -*-
"""
量比×换手率×涨跌幅 组合筛选核心逻辑

6 项过滤条件（全部通过才算命中）:
  1. 量比        MIN_VR < VR < MAX_VR
  2. 涨跌幅      MIN_PCT < pctChg < MAX_PCT
  3. 价格        close > MIN_PRICE
  4. 换手率      MIN_TURN < turn < MAX_TURN
  5. 总金额      MIN_AMOUNT < amount < MAX_AMOUNT
  6. 当日收涨    pctChg > 0%

所有阈值从外部 config dict 传入，不使用模块级常量。
"""
from __future__ import annotations

from typing import Optional
import pandas as pd

MIN_ROWS = 6   # 前5天 + 当日 = 至少 6 行


class SurgeAnalyzer:
    """量比×换手率×涨跌幅 组合筛选"""

    @staticmethod
    def analyze(df: pd.DataFrame, info: dict, cfg: dict) -> Optional[dict]:
        """执行 6 项过滤，全部命中返回结果 dict，否则 None"""
        if df is None or len(df) < MIN_ROWS:
            return None

        lookback = int(cfg.get("vr_lookback_days", 5))
        latest = df.iloc[-1]
        prev = df.iloc[-(lookback + 1):-1]

        if not _pass_all(latest, prev, cfg):
            return None

        vr = latest["volume"] / prev["volume"].mean()
        return _build_result(latest, info, vr)


def _pass_all(latest: pd.Series, prev: pd.DataFrame, cfg: dict) -> bool:
    """依次检查 6 项过滤条件"""
    return (
        _check_price(latest, cfg)
        and _check_pctchg(latest, cfg)
        and _check_turn(latest, cfg)
        and _check_amount(latest, cfg)
        and _check_positive(latest)
        and _check_volume_ratio(latest, prev, cfg)
    )


def _build_result(latest: pd.Series, info: dict, vr: float) -> dict:
    return {
        "代码":      info.get("code", ""),
        "名称":      info.get("name", ""),
        "行业":      info.get("industry", ""),
        "最新收盘":  round(float(latest["close"]), 2),
        "涨跌幅%":   round(float(latest["pctchg"]), 2),
        "量比":      round(vr, 2),
        "换手率%":   round(float(latest["turn"]), 2),
        "总金额(万)": round(float(latest["amount"]) / 1e4, 0),
        "最新日期":  str(latest["date"])[:10],
    }


# ── 单项检查函数 ────────────────────────────────
def _check_price(row: pd.Series, cfg: dict) -> bool:
    val = row.get("close")
    return val is not None and not pd.isna(val) and val > cfg["price"]["min"]


def _check_pctchg(row: pd.Series, cfg: dict) -> bool:
    val = row.get("pctchg")
    c = cfg["pct_chg"]
    return val is not None and not pd.isna(val) and c["min"] < val < c["max"]


def _check_turn(row: pd.Series, cfg: dict) -> bool:
    val = row.get("turn")
    c = cfg["turnover"]
    return val is not None and not pd.isna(val) and c["min"] < val < c["max"]


def _check_amount(row: pd.Series, cfg: dict) -> bool:
    val = row.get("amount")
    c = cfg["amount"]
    return val is not None and not pd.isna(val) and c["min"] < val < c["max"]


def _check_positive(row: pd.Series) -> bool:
    """涨速 > 0%（收盘后 = 当日收涨）"""
    val = row.get("pctchg")
    return val is not None and not pd.isna(val) and val > 0


def _check_volume_ratio(row: pd.Series, prev: pd.DataFrame, cfg: dict) -> bool:
    vol = row.get("volume")
    if vol is None or pd.isna(vol) or vol <= 0:
        return False
    avg = prev["volume"].mean()
    if pd.isna(avg) or avg <= 0:
        return False
    c = cfg["volume_ratio"]
    return c["min"] < (vol / avg) < c["max"]
