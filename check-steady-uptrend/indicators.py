# -*- coding: utf-8 -*-
"""
稳步上升（steady uptrend）指标

直接使用项目统一的技术指标库
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import sys
import numpy as np
import pandas as pd

# 添加 util 目录到路径
util_dir = Path(__file__).resolve().parent.parent / "util"
if str(util_dir) not in sys.path:
    sys.path.append(str(util_dir))

from indicators_lib import TechnicalIndicators


@dataclass
class SteadyUptrendConfig:
    ma_windows: Tuple[int, int, int, int] = (5, 10, 20, 30)
    ma_long: int = 60
    slope_lookback_short: int = 5
    slope_lookback_long: int = 10
    drawdown_lookback: int = 60
    max_drawdown: float = 0.08
    min_bars: int = 80


def compute_steady_uptrend_flags(df: pd.DataFrame, config: SteadyUptrendConfig) -> pd.DataFrame:
    df = df.copy()
    close = df["close"].astype(float)

    df_flags = TechnicalIndicators.check_steady_uptrend(
        close,
        ma_windows=config.ma_windows,
        ma_long=config.ma_long,
        slope_lookback_short=config.slope_lookback_short,
        slope_lookback_long=config.slope_lookback_long,
        drawdown_lookback=config.drawdown_lookback,
        max_drawdown=config.max_drawdown
    )

    # 合并结果到原始 DataFrame
    for col in ["ma5", "ma10", "ma20", "ma30", "ma60", 
                "slope20", "slope30", "slope60", 
                "drawdown_60", "steady_uptrend"]:
        if col in df_flags.columns:
            df[col] = df_flags[col]

    return df


def steady_uptrend_signal(df: pd.DataFrame, config: SteadyUptrendConfig) -> Dict[str, object]:
    if df is None or df.empty or len(df) < config.min_bars:
        return {
            "steady_uptrend": False,
            "reason": "数据不足",
        }

    df_flags = compute_steady_uptrend_flags(df, config)
    latest = df_flags.iloc[-1]

    return {
        "steady_uptrend": bool(latest.get("steady_uptrend", False)),
        "latest_date": latest.get("date"),
        "latest_close": float(latest.get("close", np.nan)),
        "ma5": float(latest.get("ma5", np.nan)),
        "ma10": float(latest.get("ma10", np.nan)),
        "ma20": float(latest.get("ma20", np.nan)),
        "ma30": float(latest.get("ma30", np.nan)),
        "ma60": float(latest.get("ma60", np.nan)) if not pd.isna(latest.get("ma60", np.nan)) else None,
        "slope20": float(latest.get("slope20", np.nan)),
        "slope30": float(latest.get("slope30", np.nan)),
        "slope60": float(latest.get("slope60", np.nan)) if not pd.isna(latest.get("slope60", np.nan)) else None,
        "drawdown_60": float(latest.get("drawdown_60", np.nan)),
        "order_ok": bool(latest.get("ma5", 0) > latest.get("ma10", 0) > latest.get("ma20", 0) > latest.get("ma30", 0)),
        "price_above": bool(latest.get("close", 0) > latest.get("ma20", 0) and latest.get("close", 0) > latest.get("ma30", 0)),
        "drawdown_ok": bool(latest.get("drawdown_60", 0) >= -config.max_drawdown),
    }
