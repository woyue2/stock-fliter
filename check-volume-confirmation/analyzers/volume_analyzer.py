# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  pd.DataFrame — 单股日线数据; end_date: Optional[str]; return_all: bool
# OUTPUT: Tuple[Optional[dict], Optional[str]] — 包含指标的字典（含 is_hit 字段）, 跳过原因
# POS:    check-volume-confirmation/analyzers/volume_analyzer.py（Phase 6 从 pipeline.py 提取）
# -*- coding: utf-8 -*-
"""
量价确认分析模块

策略：昨放量突破（昨量 > 前3天均量）+ 今阳线。
附加分析：试盘行为识别（来自 shipan_logic.py）+ 信心评分 + 标签。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

# 确保模块根在 path
_MOD = Path(__file__).resolve().parent.parent
if str(_MOD) not in sys.path:
    sys.path.insert(0, str(_MOD))

from shipan_logic import analyze_shipan_behavior  # noqa: E402

# ── 标签定义（写死常量，避免散落字符串） ──────────────────────────────────────
TAG_STRONG   = "多重试盘"   # shipan_count >= 3
TAG_MODERATE = "准突破"     # shipan_count 1~2
TAG_PLAIN    = "纯量价"     # shipan_count == 0


def _calc_volume_ratio(d1_vol: float, d2_vol: float, d3_vol: float, d4_vol: float) -> float:
    """昨量 / 前3天均量，衡量放量力度"""
    avg_prev = (d2_vol + d3_vol + d4_vol) / 3
    if avg_prev <= 0:
        return 0.0
    return round(d1_vol / avg_prev, 2)


def _calc_confidence(
    volume_ratio: float,
    shipan_count: int,
    shipan_detail: str,
) -> int:
    """
    信心指数 0-100，由量价特征、试盘数量、试盘类型共同决定。

    分值构成：
      基础量价分（max 60）:
        volume_ratio >= 2.0 → 60
        volume_ratio >= 1.5 → 45
        volume_ratio >= 1.2 → 30
        else                → 20

      试盘次数加分（max 30）:
        每次 +10，上限 3 次

      试盘类型加分（max 10）:
        包含"涨停" → +10
        包含"上影" → +5
    """
    # 基础分（线性平滑）：量比 1.0 -> 20分，量比 2.0 -> 60分
    # 计算公式：20 + (volume_ratio - 1.0) * 40，上限 60
    base = 20 + max(0, (volume_ratio - 1.0)) * 40
    base = min(60, int(base))

    # 试盘次数加分
    shipan_bonus = min(shipan_count * 10, 30)

    # 试盘类型加分
    type_bonus = 0
    if "涨停" in shipan_detail:
        type_bonus = 10
    elif "上影" in shipan_detail:
        type_bonus = 5

    return base + shipan_bonus + type_bonus


def _calc_tag(shipan_count: int) -> str:
    """根据试盘次数划定标签"""
    if shipan_count >= 3:
        return TAG_STRONG
    if shipan_count >= 1:
        return TAG_MODERATE
    return TAG_PLAIN


def evaluate_stock(
    df: pd.DataFrame,
    end_date: Optional[str] = None,
    return_all: bool = False,
) -> Tuple[Optional[dict], Optional[str]]:
    """
    分析股票量价特征逻辑

    Args:
        df:         单股日线 DataFrame
        end_date:   结束日期
        return_all: 是否即使不符合策略条件也返回数据（用于全量页）
    """
    if df is None or df.empty:
        return None, "无数据"

    if end_date:
        try:
            target_dt = pd.to_datetime(end_date)
            df = df[df["date"] <= target_dt].copy()
        except Exception:
            return None, "日期错误"

    if len(df) < 5:
        return None, "样本不足"

    last5 = df.tail(5).copy()
    if last5[["open", "close", "volume"]].isna().any().any():
        return None, "关键值缺失"
    
    d0 = last5.iloc[-1]
    d1 = last5.iloc[-2]
    d2 = last5.iloc[-3]
    d3 = last5.iloc[-4]
    d4 = last5.iloc[-5]

    # 核心策略条件
    yday_breakout = bool(d1["volume"] > d2["volume"] and d1["volume"] > d3["volume"] and d1["volume"] > d4["volume"])
    today_up = bool(d0["close"] > d0["open"])
    is_hit = bool(yday_breakout and today_up)

    if not is_hit and not return_all:
        return None, ("非昨放量" if not yday_breakout else "今日非阳线")

    # 计算试盘行为
    shipan_count, shipan_detail = analyze_shipan_behavior(df)

    # 计算量比放大倍数
    volume_ratio = _calc_volume_ratio(
        float(d1["volume"]), float(d2["volume"]),
        float(d3["volume"]), float(d4["volume"]),
    )

    # 信心指数与标签
    confidence = _calc_confidence(volume_ratio, shipan_count, shipan_detail)
    tag = _calc_tag(shipan_count)

    return {
        "code":          str(d0["code"]).zfill(6),
        "date_0":        pd.Timestamp(d0["date"]).strftime("%Y-%m-%d"),
        "open_0":        float(d0["open"]),
        "close_0":       float(d0["close"]),
        "volume_0":      float(d0["volume"]),
        "date_m1":       pd.Timestamp(d1["date"]).strftime("%Y-%m-%d"),
        "volume_m1":     float(d1["volume"]),
        "volume_m2":     float(d2["volume"]),
        "volume_m3":     float(d3["volume"]),
        "volume_m4":     float(d4["volume"]),
        "volume_ratio":  volume_ratio,
        "shipan_count":  shipan_count,
        "shipan_detail": shipan_detail,
        "confidence":    confidence,
        "tag":           tag,
        "is_hit":        is_hit,
        "signal":        "量价确认系统" if return_all else "昨放量+今阳线",
    }, None


def empty_result_df() -> pd.DataFrame:
    """返回空结果 DataFrame（含完整列定义）"""
    return pd.DataFrame(
        columns=[
            "code", "name", "industry", "board",
            "date_0", "open_0", "close_0", "volume_0",
            "date_m1", "volume_m1", "volume_m2", "volume_m3", "volume_m4",
            "volume_ratio", "shipan_count", "shipan_detail",
            "confidence", "tag", "signal",
        ]
    )
