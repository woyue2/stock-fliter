# -*- coding: utf-8 -*-
"""
玄学指标模块 - 统一定义和实现

术语定义：
- "阳线": 收盘价 > 开盘价 (上涨)
- "阴线": 收盘价 < 开盘价 (下跌)
- "连续6阳": 连续6天都是阳线
- "6涨1跌": 在指定窗口期内，找到连续6天阳线 + 1天阴线的模式

条件说明：
1. mystic_6up1down_in_window: 在lookback_days窗口内，存在连续6阳后1阴的模式
2. mystic_consecutive_6up: 最近6天全部是连续阳线
3. mystic_today_down_after_6up: 今天是阴线，且前6天连续阳线（刚完成6连阳后回调）
4. mystic_today_is_6th_up: 今天是阳线，且是连续第6天阳线（6连阳正在进行）
"""
from __future__ import annotations

import pandas as pd
from typing import Tuple, Optional


def is_up_day(open_price: float, close_price: float) -> bool:
    """判断是否为阳线（上涨日）"""
    return close_price > open_price


def is_down_day(open_price: float, close_price: float) -> bool:
    """判断是否为阴线（下跌日）"""
    return close_price < open_price


def get_up_down_series(open_series: pd.Series, close_series: pd.Series) -> pd.Series:
    """获取涨跌序列，True=阳线，False=阴线"""
    return close_series.astype(float) > open_series.astype(float)


def find_consecutive_up_days(up_series: pd.Series, target_length: int = 6) -> list:
    """
    找到所有连续阳线的起始位置
    返回: [(start_idx, length), ...] 其中length >= target_length
    """
    results = []
    i = 0
    n = len(up_series)
    
    while i < n:
        if up_series.iloc[i]:
            # 找到阳线，计算连续长度
            start = i
            while i < n and up_series.iloc[i]:
                i += 1
            length = i - start
            if length >= target_length:
                results.append((start, length))
        else:
            i += 1
    
    return results


def mystic_6up1down_in_window(
    open_series: pd.Series, 
    close_series: pd.Series, 
    lookback_days: int = 10
) -> bool:
    """
    玄学条件：在最近lookback_days天内，存在"连续6阳+1阴"的模式
    
    例如10天窗口：找到任意连续6天阳线后紧跟1天阴线的情况
    """
    if open_series is None or close_series is None:
        return False
    if len(open_series) < 7 or len(close_series) < 7:
        return False
    
    # 取最近lookback_days天的数据
    o = open_series.iloc[-lookback_days:].astype(float)
    c = close_series.iloc[-lookback_days:].astype(float)
    
    if len(o) < 7:
        return False
    
    up = get_up_down_series(o, c)
    
    # 滑动窗口查找：连续6阳 + 1阴
    for i in range(len(up) - 6):
        # 检查位置i开始的6天是否全部阳线
        if up.iloc[i:i + 6].all():
            # 检查第7天（如果存在）是否为阴线
            if i + 6 < len(up) and not up.iloc[i + 6]:
                return True
    
    return False


def mystic_consecutive_6up(open_series: pd.Series, close_series: pd.Series) -> bool:
    """
    玄学条件：最近6天全部是连续阳线
    """
    if open_series is None or close_series is None:
        return False
    if len(open_series) < 6 or len(close_series) < 6:
        return False
    
    o = open_series.iloc[-6:].astype(float)
    c = close_series.iloc[-6:].astype(float)
    
    return bool(get_up_down_series(o, c).all())


def mystic_today_down_after_6up(open_series: pd.Series, close_series: pd.Series) -> bool:
    """
    玄学条件：今天阴线 + 前6天连续阳线
    
    含义：6连阳后的回调日（买入机会）
    """
    if open_series is None or close_series is None:
        return False
    if len(open_series) < 7 or len(close_series) < 7:
        return False
    
    o = open_series.iloc[-7:].astype(float)
    c = close_series.iloc[-7:].astype(float)
    
    # 今天必须是阴线
    if not is_down_day(o.iloc[-1], c.iloc[-1]):
        return False
    
    # 前6天必须全部是阳线
    up_prev6 = get_up_down_series(o.iloc[:-1], c.iloc[:-1])
    return bool(up_prev6.all())


def mystic_today_is_6th_up(open_series: pd.Series, close_series: pd.Series) -> bool:
    """
    玄学条件：今天是第6天连续阳线
    
    含义：6连阳正在进行中（顺势追涨）
    """
    if open_series is None or close_series is None:
        return False
    if len(open_series) < 6 or len(close_series) < 6:
        return False
    
    o = open_series.iloc[-6:].astype(float)
    c = close_series.iloc[-6:].astype(float)
    
    # 最近6天全部阳线
    return bool(get_up_down_series(o, c).all())


def mystic_6up_prev_down(open_series: pd.Series, close_series: pd.Series) -> bool:
    """
    玄学条件：6连阳，且6连阳之前那天是阴线
    
    含义：从阴线启动的6连阳（底部启动信号）
    """
    if open_series is None or close_series is None:
        return False
    if len(open_series) < 7 or len(close_series) < 7:
        return False
    
    o = open_series.iloc[-7:].astype(float)
    c = close_series.iloc[-7:].astype(float)
    
    # 最近6天全部阳线
    if not get_up_down_series(o.iloc[-6:], c.iloc[-6:]).all():
        return False
    
    # 第-7天是阴线
    return is_down_day(o.iloc[0], c.iloc[0])


def compute_all_mystic_indicators(
    open_series: pd.Series, 
    close_series: pd.Series,
    lookback_days: int = 10
) -> dict:
    """
    计算所有玄学指标
    
    返回字典包含：
    - mystic_6up1down_10d: 10天窗口内有6连阳+1阴
    - mystic_consecutive_6up: 最近6天连续阳线
    - mystic_today_down_after_6up: 今天阴线+前6天6连阳（回调买点）
    - mystic_today_is_6th_up: 今天是第6天阳线（追涨点）
    - mystic_6up_prev_down: 6连阳前一天是阴线（底部启动）
    """
    return {
        "mystic_6up1down_10d": mystic_6up1down_in_window(open_series, close_series, lookback_days),
        "mystic_consecutive_6up": mystic_consecutive_6up(open_series, close_series),
        "mystic_today_down_after_6up": mystic_today_down_after_6up(open_series, close_series),
        "mystic_today_is_6th_up": mystic_today_is_6th_up(open_series, close_series),
        "mystic_6up_prev_down": mystic_6up_prev_down(open_series, close_series),
    }


# ============================================================
# 列名映射（中英文对照）
# ============================================================
MYSTIC_COLUMN_MAP = {
    "mystic_6up1down_10d": "玄学_10天内有6连阳后1阴",
    "mystic_consecutive_6up": "玄学_最近6天连续阳线",
    "mystic_today_down_after_6up": "玄学_今天阴线且前6天连阳(回调)",
    "mystic_today_is_6th_up": "玄学_今天是第6天阳线(等待)",
    "mystic_6up_prev_down": "玄学_6连阳前一天是阴线",
}

# 反向映射
MYSTIC_COLUMN_MAP_REVERSE = {v: k for k, v in MYSTIC_COLUMN_MAP.items()}


def get_mystic_priority(row: dict) -> Tuple[int, str]:
    """
    获取玄学优先级
    
    返回: (优先级数字, 优先级标签)
    优先级数字越小越优先
    """
    # 优先级1：今天回调（6连阳后第1天阴线）- 最佳买入机会
    if row.get("mystic_today_down_after_6up") or row.get("玄学_今天阴线且前6天连阳(回调)"):
        return (1, "[STAR]买入")
    
    # 优先级2：今天是第6天阳线 - 等待明天回调再买入
    if row.get("mystic_today_is_6th_up") or row.get("玄学_今天是第6天阳线(等待)"):
        return (2, "[STAR]等待")
    
    # 优先级3：6连阳中（但不是第6天）
    if row.get("mystic_consecutive_6up") or row.get("玄学_最近6天连续阳线"):
        return (3, "◆连阳")
    
    # 优先级4：10天内有6连阳模式
    if row.get("mystic_6up1down_10d") or row.get("玄学_10天内有6连阳后1阴"):
        return (4, "○模式")
    
    return (9, "")


if __name__ == "__main__":
    # 测试代码
    import numpy as np
    
    # 模拟数据：6连阳后1阴
    opens = pd.Series([10, 10, 10, 10, 10, 10, 10, 12])
    closes = pd.Series([11, 11, 11, 11, 11, 11, 11, 11])  # 前7天涨，最后1天跌
    
    print("测试数据：前7天涨，最后1天跌")
    results = compute_all_mystic_indicators(opens, closes)
    for k, v in results.items():
        print(f"  {k}: {v}")
