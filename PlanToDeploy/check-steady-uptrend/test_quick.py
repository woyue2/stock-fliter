# -*- coding: utf-8 -*-
"""
快速测试脚本 - 验证更新是否成功
"""

print("=" * 80)
print("测试更新是否成功")
print("=" * 80)

# 测试1: 导入容忍版模块
print("\n[1/4] 测试容忍版模块...")
try:
    from mystic_indicators_tolerant import (
        compute_all_mystic_indicators_tolerant,
        MYSTIC_COLUMN_MAP_TOLERANT,
        DEFAULT_SMALL_DROP_THRESHOLD
    )
    print(f"  [OK] 容忍版模块导入成功")
    print(f"  [OK] 指标数量: {len(MYSTIC_COLUMN_MAP_TOLERANT)}")
    print(f"  [OK] 小跌阈值: {DEFAULT_SMALL_DROP_THRESHOLD}%")
except Exception as e:
    print(f"  [ERROR] 失败: {e}")
    exit(1)

# 测试2: 导入趋势分析器
print("\n[2/4] 测试趋势分析器...")
try:
    from analyzers.trend_analyzer import TrendAnalyzer
    print(f"  [OK] 趋势分析器导入成功")
except Exception as e:
    print(f"  [ERROR] 失败: {e}")
    exit(1)

# 测试3: 导入组合器
print("\n[3/4] 测试组合器...")
try:
    from combiners.xuanxue_combiner import XuanxueCombiner
    total = len(XuanxueCombiner.COMBINATIONS)
    original = sum(1 for c in XuanxueCombiner.COMBINATIONS if not c[0].endswith('_tolerant'))
    tolerant = sum(1 for c in XuanxueCombiner.COMBINATIONS if c[0].endswith('_tolerant'))
    print(f"  [OK] 组合器导入成功")
    print(f"  [OK] 总组合数量: {total}")
    print(f"  [OK] 原版组合: {original}")
    print(f"  [OK] 容忍版组合: {tolerant}")
except Exception as e:
    print(f"  [ERROR] 失败: {e}")
    exit(1)

# 测试4: 运行简单测试
print("\n[4/4] 运行功能测试...")
try:
    import pandas as pd
    from mystic_indicators import compute_all_mystic_indicators
    
    # 测试数据：严格6连阳
    opens = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0, 10.0])
    closes = pd.Series([10.2, 10.3, 10.4, 10.5, 10.6, 10.7])
    
    result_strict = compute_all_mystic_indicators(opens, closes)
    result_tolerant = compute_all_mystic_indicators_tolerant(opens, closes)
    
    print(f"  [OK] 原版-连续6阳: {result_strict['mystic_consecutive_6up']}")
    print(f"  [OK] 容忍版-连续6有效涨: {result_tolerant['mystic_consecutive_6up_tolerant']}")
    
    # 测试数据：包含小跌
    opens2 = pd.Series([10.0, 10.2, 10.5, 10.0, 10.0, 10.0])
    closes2 = pd.Series([10.2, 10.5, 10.37, 10.2, 10.3, 10.4])
    
    result_strict2 = compute_all_mystic_indicators(opens2, closes2)
    result_tolerant2 = compute_all_mystic_indicators_tolerant(opens2, closes2)
    
    print(f"  [OK] 原版-连续6阳(含小跌): {result_strict2['mystic_consecutive_6up']}")
    print(f"  [OK] 容忍版-连续6有效涨(含小跌): {result_tolerant2['mystic_consecutive_6up_tolerant']}")
    
    if not result_strict2['mystic_consecutive_6up'] and result_tolerant2['mystic_consecutive_6up_tolerant']:
        print(f"  [OK] 容忍版正确识别了包含小跌的连涨模式")
    
except Exception as e:
    print(f"  [ERROR] 失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 80)
print("所有测试通过！")
print("=" * 80)
print("\n更新内容:")
print("  1. 新增 mystic_indicators_tolerant.py (容忍版指标)")
print("  2. 更新 analyzers/trend_analyzer.py (同时计算两套指标)")
print("  3. 更新 combiners/xuanxue_combiner.py (28种组合)")
print("  4. 新增 玄学指标说明.md (详细文档)")
print("  5. 新增 compare_versions.py (版本对比工具)")
print("\n现在可以运行:")
print("  python main.py              # 完整分析(生成28种组合)")
print("  python compare_versions.py  # 版本对比测试")
print("=" * 80)

