# -*- coding: utf-8 -*-
"""
玄学指标版本对比工具

快速对比原版（严格）和容忍版指标的差异
"""
from __future__ import annotations

import pandas as pd
from pathlib import Path

from mystic_indicators import compute_all_mystic_indicators, MYSTIC_COLUMN_MAP
from mystic_indicators_tolerant import (
    compute_all_mystic_indicators_tolerant,
    MYSTIC_COLUMN_MAP_TOLERANT,
    DEFAULT_SMALL_DROP_THRESHOLD
)


def compare_on_sample_data():
    """使用示例数据对比两个版本"""
    
    print("=" * 80)
    print("玄学指标版本对比测试")
    print("=" * 80)
    
    # 测试用例1：严格6连阳（两个版本都应该通过）
    print("\n【测试1】严格6连阳（预期：两个版本都通过）")
    opens_1 = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0, 10.0])
    closes_1 = pd.Series([10.2, 10.3, 10.4, 10.5, 10.6, 10.7])
    
    result_strict_1 = compute_all_mystic_indicators(opens_1, closes_1)
    result_tolerant_1 = compute_all_mystic_indicators_tolerant(opens_1, closes_1)
    
    print(f"  原版-连续6阳: {result_strict_1['mystic_consecutive_6up']}")
    print(f"  容忍版-连续6有效涨: {result_tolerant_1['mystic_consecutive_6up_tolerant']}")
    
    # 测试用例2：包含1.2%小跌（原版不通过，容忍版通过）
    print("\n【测试2】包含1.2%小跌（预期：原版不通过，容忍版通过）")
    opens_2 = pd.Series([10.0, 10.2, 10.5, 10.0, 10.0, 10.0])
    closes_2 = pd.Series([10.2, 10.5, 10.37, 10.2, 10.3, 10.4])  # Day3: 跌1.24%
    
    result_strict_2 = compute_all_mystic_indicators(opens_2, closes_2)
    result_tolerant_2 = compute_all_mystic_indicators_tolerant(opens_2, closes_2)
    
    drop_pct = (10.5 - 10.37) / 10.5 * 100
    print(f"  Day3跌幅: {drop_pct:.2f}%")
    print(f"  原版-连续6阳: {result_strict_2['mystic_consecutive_6up']}")
    print(f"  容忍版-连续6有效涨: {result_tolerant_2['mystic_consecutive_6up_tolerant']}")
    
    # 测试用例3：包含2.0%大跌（两个版本都不通过）
    print("\n【测试3】包含2.0%大跌（预期：两个版本都不通过）")
    opens_3 = pd.Series([10.0, 10.2, 10.5, 10.0, 10.0, 10.0])
    closes_3 = pd.Series([10.2, 10.5, 10.29, 10.2, 10.3, 10.4])  # Day3: 跌2.0%
    
    result_strict_3 = compute_all_mystic_indicators(opens_3, closes_3)
    result_tolerant_3 = compute_all_mystic_indicators_tolerant(opens_3, closes_3)
    
    drop_pct = (10.5 - 10.29) / 10.5 * 100
    print(f"  Day3跌幅: {drop_pct:.2f}%")
    print(f"  原版-连续6阳: {result_strict_3['mystic_consecutive_6up']}")
    print(f"  容忍版-连续6有效涨: {result_tolerant_3['mystic_consecutive_6up_tolerant']}")
    
    # 测试用例4：多个小跌（原版不通过，容忍版通过）
    print("\n【测试4】包含两个小跌（预期：原版不通过，容忍版通过）")
    opens_4 = pd.Series([10.0, 10.2, 10.0, 10.5, 10.0, 10.0])
    closes_4 = pd.Series([10.2, 10.15, 10.2, 10.45, 10.2, 10.3])  # Day2和Day4小跌
    
    result_strict_4 = compute_all_mystic_indicators(opens_4, closes_4)
    result_tolerant_4 = compute_all_mystic_indicators_tolerant(opens_4, closes_4)
    
    drop_pct_2 = (10.2 - 10.15) / 10.2 * 100
    drop_pct_4 = (10.5 - 10.45) / 10.5 * 100
    print(f"  Day2跌幅: {drop_pct_2:.2f}%, Day4跌幅: {drop_pct_4:.2f}%")
    print(f"  原版-连续6阳: {result_strict_4['mystic_consecutive_6up']}")
    print(f"  容忍版-连续6有效涨: {result_tolerant_4['mystic_consecutive_6up_tolerant']}")
    
    # 汇总对比
    print("\n" + "=" * 80)
    print("对比总结")
    print("=" * 80)
    print("\n原版指标（严格）：")
    for eng_name, cn_name in MYSTIC_COLUMN_MAP.items():
        print(f"  - {eng_name:30s} → {cn_name}")
    
    print("\n容忍版指标（允许小跌<1.64%）：")
    for eng_name, cn_name in MYSTIC_COLUMN_MAP_TOLERANT.items():
        print(f"  - {eng_name:40s} → {cn_name}")
    
    print("\n" + "=" * 80)
    print("结论：")
    print("  1. 原版适合寻找强势连续上涨的股票（精准但覆盖面窄）")
    print("  2. 容忍版适合寻找稳健上涨但允许小幅震荡的股票（覆盖面广）")
    print("  3. 建议同时使用两个版本，对比观察效果")
    print("=" * 80)


def compare_on_real_stock(code: str):
    """对比真实股票数据"""
    from data_loader import load_daily_data
    
    print(f"\n对比真实股票: {code}")
    print("-" * 80)
    
    df = load_daily_data(code)
    if df.empty or len(df) < 10:
        print(f"  [ERROR] 股票 {code} 数据不足")
        return
    
    df = df.tail(10).copy()
    open_series = df["open"].astype(float)
    close_series = df["close"].astype(float)
    
    # 计算两个版本的指标
    result_strict = compute_all_mystic_indicators(open_series, close_series)
    result_tolerant = compute_all_mystic_indicators_tolerant(open_series, close_series)
    
    # 显示最近10天的涨跌情况
    print("\n最近10天涨跌情况：")
    print(f"  {'日期':<12} {'开盘':<8} {'收盘':<8} {'涨跌':<8} {'跌幅%':<8} {'原版':<8} {'容忍版':<8}")
    print("  " + "-" * 70)
    
    for i in range(len(df)):
        date = df.iloc[i]["date"]
        o = open_series.iloc[i]
        c = close_series.iloc[i]
        
        if c >= o:
            status = "涨"
            pct = (c - o) / o * 100
            strict_status = "✓"
            tolerant_status = "✓"
        else:
            status = "跌"
            pct = (o - c) / o * 100
            strict_status = "✗"
            tolerant_status = "✓" if pct < DEFAULT_SMALL_DROP_THRESHOLD else "✗"
        
        print(f"  {date:<12} {o:<8.2f} {c:<8.2f} {status:<8} {pct:<8.2f} {strict_status:<8} {tolerant_status:<8}")
    
    # 显示指标结果
    print("\n原版指标结果：")
    for key, value in result_strict.items():
        cn_name = MYSTIC_COLUMN_MAP.get(key, key)
        print(f"  {cn_name}: {value}")
    
    print("\n容忍版指标结果：")
    for key, value in result_tolerant.items():
        cn_name = MYSTIC_COLUMN_MAP_TOLERANT.get(key, key)
        print(f"  {cn_name}: {value}")
    
    print("-" * 80)


if __name__ == "__main__":
    import sys
    
    # 示例数据对比
    compare_on_sample_data()
    
    # 如果提供了股票代码，对比真实数据
    if len(sys.argv) > 1:
        code = sys.argv[1]
        compare_on_real_stock(code)
    else:
        print("\n提示：可以传入股票代码对比真实数据")
        print("  用法: python compare_versions.py 000001")

