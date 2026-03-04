# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  pd.DataFrame — 单股日线数据（需含 date/open/close/volume 列）；end_date: Optional[str]
# OUTPUT: Tuple[Optional[dict], Optional[str]] — (命中结果行, 跳过原因)
# POS:    check-volume-confirmation/analyzers/volume_analyzer.py（Phase 6 从 pipeline.py 提取）
# -*- coding: utf-8 -*-
"""
量价确认分析模块

策略：昨放量突破（昨量 > 前3天均量）+ 今阳线。
附加分析：试盘行为识别（来自 shipan_logic.py）。
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


def evaluate_stock(
    df: pd.DataFrame,
    end_date: Optional[str] = None,
) -> Tuple[Optional[dict], Optional[str]]:
    """
    判断单只股票是否命中"昨放量+今阳线"策略

    Args:
        df:       单股日线 DataFrame，列需含 date/open/close/volume
        end_date: 截断日期 YYYY-MM-DD（None=使用全部数据）

    Returns:
        (result_row, None)  — 命中时返回数据行，跳过原因为 None
        (None, reason)      — 未命中时返回 None，附带跳过原因字符串
    """
    if df is None or df.empty:
        return None, "无数据"

    # 如果指定了结束日期，截断数据
    if end_date:
        try:
            target_dt = pd.to_datetime(end_date)
            df = df[df["date"] <= target_dt].copy()
        except Exception:
            return None, "结束日期格式错误"

    if len(df) < 5:
        return None, "样本不足5天"

    last5 = df.tail(5).copy()
    if last5[["open", "close", "volume"]].isna().any().any():
        return None, "关键值缺失"
    if (last5["volume"] <= 0).any():
        return None, "成交量无效"

    d0 = last5.iloc[-1]   # 今天
    d1 = last5.iloc[-2]   # 昨天
    d2 = last5.iloc[-3]
    d3 = last5.iloc[-4]
    d4 = last5.iloc[-5]

    # 核心条件：昨放量 + 今阳线
    yday_breakout = bool(
        d1["volume"] > d2["volume"]
        and d1["volume"] > d3["volume"]
        and d1["volume"] > d4["volume"]
    )
    today_up = bool(d0["close"] > d0["open"])

    if not (yday_breakout and today_up):
        reason = "非昨放量" if not yday_breakout else "今日非阳线"
        return None, reason

    # 计算试盘行为
    shipan_count, shipan_detail = analyze_shipan_behavior(df)

    return {
        "code": str(d0["code"]).zfill(6),
        "date_0": pd.Timestamp(d0["date"]).strftime("%Y-%m-%d"),
        "open_0": float(d0["open"]),
        "close_0": float(d0["close"]),
        "volume_0": float(d0["volume"]),
        "date_m1": pd.Timestamp(d1["date"]).strftime("%Y-%m-%d"),
        "volume_m1": float(d1["volume"]),
        "volume_m2": float(d2["volume"]),
        "volume_m3": float(d3["volume"]),
        "volume_m4": float(d4["volume"]),
        "shipan_count": shipan_count,
        "shipan_detail": shipan_detail,
        "signal": "昨放量+今阳线",
    }, None


def empty_result_df() -> pd.DataFrame:
    """返回空结果 DataFrame（含完整列定义）"""
    return pd.DataFrame(
        columns=[
            "code", "name", "industry", "board",
            "date_0", "open_0", "close_0", "volume_0",
            "date_m1", "volume_m1", "volume_m2", "volume_m3", "volume_m4",
            "shipan_count", "shipan_detail", "signal",
        ]
    )
