# -*- coding: utf-8 -*-
"""
6U1D模糊指标模块 - 模糊模式版本

术语定义：
- "阳线": 收盘价 > 开盘价 (上涨)
- "阴线": 收盘价 < 开盘价 (下跌)
- "小跌": 跌幅 < 阈值（默认1.64%）的阴线，可以忽略
- "有效连涨": 连续上涨，允许中间出现小跌
- "连续6有效涨": 连续6天都是阳线或小跌

核心思想：
在原有"连续6阳"策略基础上，容忍小幅度的回调。
如果出现"涨-跌-涨"模式，且中间的跌幅 < 1.64%，则忽略该跌，视作连续上涨的一部分。

示例：
- 原策略：Day1涨 → Day2涨 → Day3涨 → Day4涨 → Day5涨 → Day6涨 ✅
- 新策略：Day1涨 → Day2涨 → Day3跌(-1.2%) → Day4涨 → Day5涨 → Day6涨 ✅
         （Day3跌幅1.2% < 1.64%，可忽略）

条件说明：
1. pattern_6u1d_fuzzy_6up1down_in_window_tolerant: 在窗口内，存在连续6有效涨后1真跌的模式
2. pattern_6u1d_fuzzy_consecutive_6up_tolerant: 最近6天全部是有效连涨（可含小跌）
3. pattern_6u1d_fuzzy_today_small_drop_after_6up: 今天小跌，且前6天有效连涨（买入机会）
4. pattern_6u1d_fuzzy_today_is_6th_up_tolerant: 今天是第6天有效涨（等待回调）
"""
from __future__ import annotations

import pandas as pd
from typing import Tuple, Optional

# 默认小跌阈值：1.64%
DEFAULT_SMALL_DROP_THRESHOLD = 1.64


def is_up_day(open_price: float, close_price: float) -> bool:
    """判断是否为阳线（上涨日）"""
    return close_price > open_price


def is_down_day(open_price: float, close_price: float) -> bool:
    """判断是否为阴线（下跌日）"""
    return close_price < open_price


def calculate_drop_percentage(open_price: float, close_price: float) -> float:
    """
    计算跌幅百分比
    
    返回：
        跌幅百分比（正数表示下跌）
        如果是上涨，返回0
    """
    if close_price >= open_price:
        return 0.0
    
    if open_price == 0:
        return 0.0
    
    drop_pct = (open_price - close_price) / open_price * 100
    return drop_pct


def is_ignorable_small_drop(
    open_price: float, 
    close_price: float, 
    threshold_pct: float = DEFAULT_SMALL_DROP_THRESHOLD
) -> bool:
    """
    判断是否为可忽略的小跌
    
    参数：
        open_price: 开盘价
        close_price: 收盘价
        threshold_pct: 跌幅阈值（百分比，如1.64表示1.64%）
    
    返回：
        True: 是小跌且可忽略
        False: 不是小跌（可能是大跌或上涨）
    """
    if close_price >= open_price:
        return False  # 不是跌，是涨或平
    
    drop_pct = calculate_drop_percentage(open_price, close_price)
    
    return drop_pct < threshold_pct


def get_effective_up_down_series(
    open_series: pd.Series, 
    close_series: pd.Series, 
    small_drop_threshold: float = DEFAULT_SMALL_DROP_THRESHOLD
) -> pd.Series:
    """
    获取"有效涨跌"序列，将小跌视为上涨
    
    参数：
        open_series: 开盘价序列
        close_series: 收盘价序列
        small_drop_threshold: 小跌阈值（%）
    
    返回：
        pd.Series: True=有效上涨（包括真涨+小跌），False=真正的下跌
    
    逻辑：
        1. 如果 close >= open：True（真涨或平）
        2. 如果 close < open 且跌幅 < 阈值：True（小跌，视为涨）
        3. 如果 close < open 且跌幅 >= 阈值：False（大跌）
    """
    result = []
    
    for i in range(len(open_series)):
        o = float(open_series.iloc[i])
        c = float(close_series.iloc[i])
        
        if c >= o:
            # 真涨或平
            result.append(True)
        else:
            # 下跌，判断是否为小跌
            drop_pct = calculate_drop_percentage(o, c)
            if drop_pct < small_drop_threshold:
                result.append(True)   # 小跌，视为涨
            else:
                result.append(False)  # 大跌
    
    return pd.Series(result, index=open_series.index)


def pattern_6u1d_fuzzy_consecutive_6up_tolerant(
    open_series: pd.Series, 
    close_series: pd.Series, 
    small_drop_threshold: float = DEFAULT_SMALL_DROP_THRESHOLD
) -> bool:
    """
    6U1D模糊条件（模糊版）：最近6天"有效连续上涨"
    
    与原版 pattern_6u1d_fuzzy_consecutive_6up 的区别：
        - 原版：严格要求6天全部阳线
        - 新版：允许小跌，只要跌幅 < 阈值
    
    参数：
        open_series: 开盘价序列
        close_series: 收盘价序列
        small_drop_threshold: 小跌阈值（%），默认1.64%
    
    返回：
        bool: True=满足条件，False=不满足
    """
    if open_series is None or close_series is None:
        return False
    if len(open_series) < 6 or len(close_series) < 6:
        return False
    
    # 取最近6天
    o = open_series.iloc[-6:].astype(float)
    c = close_series.iloc[-6:].astype(float)
    
    # 获取"有效涨跌"序列（小跌视为涨）
    effective_up = get_effective_up_down_series(o, c, small_drop_threshold)
    
    # 判断是否全部为"有效上涨"
    return bool(effective_up.all())


def pattern_6u1d_fuzzy_6up1down_in_window_tolerant(
    open_series: pd.Series, 
    close_series: pd.Series, 
    lookback_days: int = 10,
    small_drop_threshold: float = DEFAULT_SMALL_DROP_THRESHOLD
) -> bool:
    """
    6U1D模糊条件（模糊版）：在窗口内存在"6有效涨+1真跌"模式
    
    与原版的区别：
        - 6涨中可以包含小跌（跌幅 < 阈值）
        - 最后的1跌必须是真跌（跌幅 >= 阈值）
    
    参数：
        open_series: 开盘价序列
        close_series: 收盘价序列
        lookback_days: 回溯天数
        small_drop_threshold: 小跌阈值（%）
    
    返回：
        bool: True=满足条件，False=不满足
    """
    if open_series is None or close_series is None:
        return False
    if len(open_series) < 7 or len(close_series) < 7:
        return False
    
    # 取最近lookback_days天
    o = open_series.iloc[-lookback_days:].astype(float)
    c = close_series.iloc[-lookback_days:].astype(float)
    
    if len(o) < 7:
        return False
    
    # 获取"有效涨跌"序列
    effective_up = get_effective_up_down_series(o, c, small_drop_threshold)
    
    # 滑动窗口查找：连续6有效涨 + 1真跌
    for i in range(len(effective_up) - 6):
        # 检查前6天是否全部"有效上涨"
        if effective_up.iloc[i:i + 6].all():
            # 检查第7天是否为"真跌"（不是有效上涨）
            if i + 6 < len(effective_up) and not effective_up.iloc[i + 6]:
                return True
    
    return False


def pattern_6u1d_fuzzy_today_small_drop_after_6up_tolerant(
    open_series: pd.Series, 
    close_series: pd.Series,
    small_drop_threshold: float = DEFAULT_SMALL_DROP_THRESHOLD
) -> bool:
    """
    6U1D模糊条件（模糊版）：今天小跌 + 前6天有效连涨
    
    含义：6连涨后的小幅回调（可能是买入机会）
    
    与原版 pattern_6u1d_fuzzy_today_down_after_6up 的区别：
        - 原版：今天必须是阴线，前6天严格阳线
        - 新版：今天是小跌，前6天有效连涨（可含小跌）
    
    参数：
        open_series: 开盘价序列
        close_series: 收盘价序列
        small_drop_threshold: 小跌阈值（%）
    
    返回：
        bool: True=满足条件，False=不满足
    """
    if open_series is None or close_series is None:
        return False
    if len(open_series) < 7 or len(close_series) < 7:
        return False
    
    o = open_series.iloc[-7:].astype(float)
    c = close_series.iloc[-7:].astype(float)
    
    # 今天必须是小跌
    today_o = o.iloc[-1]
    today_c = c.iloc[-1]
    if not is_ignorable_small_drop(today_o, today_c, small_drop_threshold):
        return False
    
    # 前6天必须全部"有效上涨"
    effective_up_prev6 = get_effective_up_down_series(
        o.iloc[:-1], 
        c.iloc[:-1], 
        small_drop_threshold
    )
    
    return bool(effective_up_prev6.all())


def pattern_6u1d_fuzzy_today_is_6th_up_tolerant(
    open_series: pd.Series, 
    close_series: pd.Series,
    small_drop_threshold: float = DEFAULT_SMALL_DROP_THRESHOLD
) -> bool:
    """
    6U1D模糊条件（模糊版）：今天是第6天有效连涨
    
    含义：6有效连涨正在进行中（等待回调）
    
    参数：
        open_series: 开盘价序列
        close_series: 收盘价序列
        small_drop_threshold: 小跌阈值（%）
    
    返回：
        bool: True=满足条件，False=不满足
    """
    if open_series is None or close_series is None:
        return False
    if len(open_series) < 6 or len(close_series) < 6:
        return False
    
    o = open_series.iloc[-6:].astype(float)
    c = close_series.iloc[-6:].astype(float)
    
    # 最近6天全部"有效上涨"
    effective_up = get_effective_up_down_series(o, c, small_drop_threshold)
    return bool(effective_up.all())


def pattern_6u1d_fuzzy_6up_prev_down_tolerant(
    open_series: pd.Series, 
    close_series: pd.Series,
    small_drop_threshold: float = DEFAULT_SMALL_DROP_THRESHOLD
) -> bool:
    """
    6U1D模糊条件（模糊版）：6有效连涨，且之前那天是真跌
    
    含义：从真跌启动的6有效连涨（底部启动信号）
    
    参数：
        open_series: 开盘价序列
        close_series: 收盘价序列
        small_drop_threshold: 小跌阈值（%）
    
    返回：
        bool: True=满足条件，False=不满足
    """
    if open_series is None or close_series is None:
        return False
    if len(open_series) < 7 or len(close_series) < 7:
        return False
    
    o = open_series.iloc[-7:].astype(float)
    c = close_series.iloc[-7:].astype(float)
    
    # 最近6天全部"有效上涨"
    effective_up_6 = get_effective_up_down_series(
        o.iloc[-6:], 
        c.iloc[-6:], 
        small_drop_threshold
    )
    if not effective_up_6.all():
        return False
    
    # 第-7天是真跌（不是有效上涨）
    effective_up_7 = get_effective_up_down_series(
        o.iloc[:1], 
        c.iloc[:1], 
        small_drop_threshold
    )
    return not bool(effective_up_7.iloc[0])


def compute_all_6u1d_indicators_fuzzy(
    open_series: pd.Series, 
    close_series: pd.Series,
    lookback_days: int = 10,
    small_drop_threshold: float = DEFAULT_SMALL_DROP_THRESHOLD
) -> dict:
    """
    计算所有6U1D模糊指标（模糊模式版本）
    
    参数：
        open_series: 开盘价序列
        close_series: 收盘价序列
        lookback_days: 回溯天数
        small_drop_threshold: 小跌阈值（%），默认1.64%
    
    返回：
        dict: 包含所有指标的字典
    """
    return {
        "pattern_6u1d_fuzzy_6up1down_10d_tolerant": pattern_6u1d_fuzzy_6up1down_in_window_tolerant(
            open_series, close_series, lookback_days, small_drop_threshold
        ),
        "pattern_6u1d_fuzzy_consecutive_6up_tolerant": pattern_6u1d_fuzzy_consecutive_6up_tolerant(
            open_series, close_series, small_drop_threshold
        ),
        "pattern_6u1d_fuzzy_today_small_drop_after_6up": pattern_6u1d_fuzzy_today_small_drop_after_6up_tolerant(
            open_series, close_series, small_drop_threshold
        ),
        "pattern_6u1d_fuzzy_today_is_6th_up_tolerant": pattern_6u1d_fuzzy_today_is_6th_up_tolerant(
            open_series, close_series, small_drop_threshold
        ),
        "pattern_6u1d_fuzzy_6up_prev_down_tolerant": pattern_6u1d_fuzzy_6up_prev_down_tolerant(
            open_series, close_series, small_drop_threshold
        ),
    }


# ============================================================
# 列名映射（中英文对照）
# ============================================================
PATTERN_6U1D_FUZZY_COLUMN_MAP = {
    "pattern_6u1d_fuzzy_6up1down_10d_tolerant": "6U1D模糊_10天内有6连涨后1跌(模糊模式)",
    "pattern_6u1d_fuzzy_consecutive_6up_tolerant": "6U1D模糊_最近6天连续涨(模糊模式)",
    "pattern_6u1d_fuzzy_today_small_drop_after_6up": "6U1D模糊_今天小跌且前6天连涨(买入机会)",
    "pattern_6u1d_fuzzy_today_is_6th_up_tolerant": "6U1D模糊_今天是第6天涨(等待)",
    "pattern_6u1d_fuzzy_6up_prev_down_tolerant": "6U1D模糊_6连涨前一天是真跌",
}

# 反向映射
PATTERN_6U1D_FUZZY_COLUMN_MAP_REVERSE = {v: k for k, v in PATTERN_6U1D_FUZZY_COLUMN_MAP.items()}


def get_6u1d_fuzzy_priority(row: dict) -> Tuple[int, str]:
    """
    获取6U1D模糊优先级（模糊版）
    
    返回: (优先级数字, 优先级标签)
    优先级数字越小越优先
    """
    # 优先级1：今天小跌且前6天连涨 - 最佳买入机会
    if row.get("pattern_6u1d_fuzzy_today_small_drop_after_6up") or row.get("6U1D模糊_今天小跌且前6天连涨(买入机会)"):
        return (1, "[STAR]买入-小回调")
    
    # 优先级2：今天是第6天有效涨 - 等待回调
    if row.get("pattern_6u1d_fuzzy_today_is_6th_up_tolerant") or row.get("6U1D模糊_今天是第6天涨(等待)"):
        return (2, "[STAR]等待-连涨中")
    
    # 优先级3：最近6天有效连涨
    if row.get("pattern_6u1d_fuzzy_consecutive_6up_tolerant") or row.get("6U1D模糊_最近6天连续涨(模糊模式)"):
        return (3, "◆连涨中")
    
    # 优先级4：10天内有6连涨模式
    if row.get("pattern_6u1d_fuzzy_6up1down_10d_tolerant") or row.get("6U1D模糊_10天内有6连涨后1跌(模糊模式)"):
        return (4, "○模式")
    
    return (9, "")


if __name__ == "__main__":
    # 测试代码
    import numpy as np
    
    print("=" * 60)
    print("模糊模式版本测试 - 阈值: 1.64%")
    print("=" * 60)
    
    # 测试用例1：包含一个小跌（1.2%）
    print("\n测试1：包含1.2%小跌（应该通过）")
    opens_1 = pd.Series([10.0, 10.2, 10.5, 10.0, 10.0, 10.0])
    closes_1 = pd.Series([10.2, 10.5, 10.37, 10.2, 10.3, 10.4])  # Day3: 10.5开->10.37收，跌约1.24%
    
    result_1 = pattern_6u1d_fuzzy_consecutive_6up_tolerant(opens_1, closes_1, small_drop_threshold=1.64)
    print(f"  结果: {result_1} (预期: True)")
    
    # 计算实际跌幅
    drop_pct_1 = (10.5 - 10.37) / 10.5 * 100
    print(f"  Day3实际跌幅: {drop_pct_1:.2f}%")
    
    # 测试用例2：包含一个大跌（2%）
    print("\n测试2：包含2%大跌（应该不通过）")
    opens_2 = pd.Series([10.0, 10.2, 10.5, 10.0, 10.0, 10.0])
    closes_2 = pd.Series([10.2, 10.5, 10.29, 10.2, 10.3, 10.4])  # Day3: 10.5开->10.29收，跌约2%
    
    result_2 = pattern_6u1d_fuzzy_consecutive_6up_tolerant(opens_2, closes_2, small_drop_threshold=1.64)
    print(f"  结果: {result_2} (预期: False)")
    
    # 计算实际跌幅
    drop_pct_2 = (10.5 - 10.29) / 10.5 * 100
    print(f"  Day3实际跌幅: {drop_pct_2:.2f}%")
    
    # 测试用例3：严格6连阳
    print("\n测试3：严格6连阳（应该通过）")
    opens_3 = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0, 10.0])
    closes_3 = pd.Series([10.2, 10.3, 10.4, 10.5, 10.6, 10.7])
    
    result_3 = pattern_6u1d_fuzzy_consecutive_6up_tolerant(opens_3, closes_3, small_drop_threshold=1.64)
    print(f"  结果: {result_3} (预期: True)")
    
    # 测试用例4：多个小跌
    print("\n测试4：包含两个小跌（0.5%和1.0%）（应该通过）")
    opens_4 = pd.Series([10.0, 10.2, 10.0, 10.5, 10.0, 10.0])
    closes_4 = pd.Series([10.2, 10.15, 10.2, 10.45, 10.2, 10.3])  # Day2和Day4小跌
    
    result_4 = pattern_6u1d_fuzzy_consecutive_6up_tolerant(opens_4, closes_4, small_drop_threshold=1.64)
    print(f"  结果: {result_4} (预期: True)")
    
    drop_pct_4_1 = (10.2 - 10.15) / 10.2 * 100
    drop_pct_4_2 = (10.5 - 10.45) / 10.5 * 100
    print(f"  Day2实际跌幅: {drop_pct_4_1:.2f}%, Day4实际跌幅: {drop_pct_4_2:.2f}%")
    
    # 测试用例5：完整指标测试
    print("\n测试5：完整指标测试（6涨+1跌模式）")
    opens_5 = pd.Series([10.0, 10.2, 10.5, 10.0, 10.0, 10.0, 10.0, 10.5])
    closes_5 = pd.Series([10.2, 10.15, 10.6, 10.2, 10.3, 10.4, 10.5, 10.3])  # 前6天涨（Day2小跌），第7天涨，第8天大跌
    
    indicators = compute_all_6u1d_indicators_fuzzy(opens_5, closes_5, lookback_days=10, small_drop_threshold=1.64)
    print("  所有指标结果:")
    for k, v in indicators.items():
        print(f"    {k}: {v}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

