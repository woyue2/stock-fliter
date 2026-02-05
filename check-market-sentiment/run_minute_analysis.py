#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分钟级走势分析演示脚本

使用方法：
python run_minute_analysis.py --help
"""
import sys
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from minute_pattern_analyzer import MinutePatternAnalyzer, MinuteDataLoader


def parse_args():
    parser = argparse.ArgumentParser(
        description="分钟级走势形态分析 - 基于240维向量",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python run_minute_analysis.py                    # 运行演示
  python run_minute_analysis.py --pattern single   # 只运行单边上涨演示
  python run_minute_analysis.py --compare          # 运行相似度比较
        """
    )
    
    parser.add_argument(
        "--pattern", "-p",
        type=str,
        choices=["all", "single", "v_shape", "consolidation", "compare"],
        default="all",
        help="运行特定演示"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output",
        help="输出目录"
    )
    
    return parser.parse_args()


def demo_single_stock():
    """演示：单只股票分析"""
    print("\n" + "=" * 60)
    print("【单只股票分钟级走势分析】")
    print("=" * 60)
    
    analyzer = MinutePatternAnalyzer(normalize=True)
    
    # 生成模拟的单边上涨走势
    np.random.seed(42)
    uptrend = np.linspace(0, 2, 240) + np.random.randn(240) * 0.1
    
    # 分析
    result = analyzer.analyze_single_stock(pd.DataFrame({'close': uptrend}))
    
    print(f"\n形态识别结果: {result['pattern_name']}")
    print(f"形态代码: {result['pattern_code']}")
    
    print(f"\n【关键指标】")
    print(f"  日内收益: {result['features']['intraday_return']:.2f}%")
    print(f"  趋势斜率: {result['features']['trend_slope']:.4f}")
    print(f"  波动率: {result['features']['volatility']:.2f}")
    print(f"  最大涨幅: {result['features']['max_gain']:.2f}%")
    print(f"  最大回撤: {result['features']['max_drawdown']:.2f}%")
    
    print(f"\n【早盘vs午盘】")
    print(f"  早盘平均: {result['features']['morning_mean']:.2f}%")
    print(f"  午盘平均: {result['features']['afternoon_mean']:.2f}%")
    print(f"  差异: {result['features']['morning_afternoon_diff']:.2f}%")
    print(f"  结论: {'早盘更强' if result['features']['morning_afternoon_diff'] > 0 else '午盘更强'}")
    
    print(f"\n【与典型形态相似度】")
    for pattern_type, similarity in result['similarities'].items():
        name = analyzer.PATTERN_NAMES.get(pattern_type, pattern_type)
        bar = "█" * int(similarity * 20)
        print(f"  {name}: {similarity:.3f} {bar}")


def demo_v_shape():
    """演示：V型反转分析"""
    print("\n" + "=" * 60)
    print("【V型反转走势分析】")
    print("=" * 60)
    
    analyzer = MinutePatternAnalyzer(normalize=True)
    
    # V型反转
    v_shape = analyzer._create_v_shape(240) + np.random.randn(240) * 0.1
    result = analyzer.analyze_single_stock(pd.DataFrame({'close': v_shape}))
    
    print(f"\n形态识别结果: {result['pattern_name']}")
    
    print(f"\n【V型特征检测】")
    print(f"  V型形状: {'是' if result['features']['v_shape'] else '否'}")
    print(f"  最低点位置: {result['features']['v_position']:.1%} (0=开盘, 1=收盘)")
    print(f"  早盘平均: {result['features']['morning_mean']:.2f}%")
    print(f"  午盘平均: {result['features']['afternoon_mean']:.2f}%")
    print(f"  早盘→午盘变化: {result['features']['morning_afternoon_diff']:+.2f}%")
    
    # 分析V型反转的强度
    if result['features']['v_position'] < 0.4:
        print(f"\n  ✓ V型底部在早盘形成，反弹充分")
    elif result['features']['v_position'] < 0.6:
        print(f"\n  ✓ V型底部在午盘形成，反弹一般")
    else:
        print(f"\n  ⚠ V型底部形成太晚，可能反弹不足")


def demo_consolidation():
    """演示：震荡整理分析"""
    print("\n" + "=" * 60)
    print("【震荡整理走势分析】")
    print("=" * 60)
    
    analyzer = MinutePatternAnalyzer(normalize=True)
    
    # 震荡整理
    consolidation = np.sin(np.linspace(0, 4*np.pi, 240)) * 0.5 + np.random.randn(240) * 0.1
    result = analyzer.analyze_single_stock(pd.DataFrame({'close': consolidation}))
    
    print(f"\n形态识别结果: {result['pattern_name']}")
    
    print(f"\n【震荡特征】")
    print(f"  波动率: {result['features']['volatility']:.2f}")
    print(f"  价格区间: {result['features']['min']:.2f}% ~ {result['features']['max']:.2f}%")
    print(f"  振幅: {result['features']['range']:.2f}%")
    print(f"  趋势斜率: {result['features']['trend_slope']:.4f} ({result['features']['trend_direction']})")
    
    print(f"\n【动量分析】")
    print(f"  30分钟平均动量: {result['features']['avg_momentum_30']:.3f}")
    print(f"  动量波动: {result['features']['momentum_30_std']:.3f}")


def demo_compare():
    """演示：走势相似度比较"""
    print("\n" + "=" * 60)
    print("【股票走势相似度比较】")
    print("=" * 60)
    
    analyzer = MinutePatternAnalyzer(normalize=True)
    np.random.seed(42)
    
    # 生成不同类型的走势
    patterns = {
        '单边上涨': np.linspace(0, 2, 240) + np.random.randn(240) * 0.1,
        '温和上涨': np.linspace(0, 1, 240) + np.random.randn(240) * 0.1,
        'V型反转': analyzer._create_v_shape(240) + np.random.randn(240) * 0.1,
        '倒V型': analyzer._create_inverted_v(240) + np.random.randn(240) * 0.1,
        '震荡整理': np.sin(np.linspace(0, 4*np.pi, 240)) * 0.5 + np.random.randn(240) * 0.1,
    }
    
    print("\n【相似度矩阵】")
    print(f"{'走势类型':<12}", end="")
    for name in patterns.keys():
        print(f"{name[:6]:<8}", end="")
    print()
    print("-" * 60)
    
    for name1, vec1 in patterns.items():
        print(f"{name1:<12}", end="")
        for name2, vec2 in patterns.items():
            sim = analyzer.compare_stocks(vec1, vec2)
            cos_sim = sim['cosine_similarity']
            print(f"{cos_sim:>7.3f}  ", end="")
        print()
    
    print("\n【解读】")
    print("  相似度 > 0.9: 走势高度相似")
    print("  相似度 0.7-0.9: 走势较为相似")
    print("  相似度 0.5-0.7: 走势有一定差异")
    print("  相似度 < 0.5: 走势差异明显")
    
    # 聚类分析
    print("\n【走势聚类分析】")
    vectors = list(patterns.values())
    labels, centers = analyzer.cluster_patterns(vectors, n_clusters=3)
    
    print(f"  聚类数量: 3")
    for i, (name, label) in enumerate(zip(patterns.keys(), labels)):
        print(f"    {name}: 类别 {label}")
    
    print("\n  ✓ 可以用于发现走势相似的股票群体")


def demo_estimate_from_daily():
    """演示：从日K数据估算分钟级走势"""
    print("\n" + "=" * 60)
    print("【从日K估算分钟级走势】")
    print("=" * 60)
    
    loader = MinuteDataLoader(".")
    analyzer = MinutePatternAnalyzer(normalize=True)
    
    # 模拟日K数据
    daily_data = pd.DataFrame({
        'open': [100, 102],
        'close': [105, 103],
        'high': [108, 106],
        'low': [99, 101],
    })
    
    print("\n【输入日K数据】")
    print(f"  开盘价: {daily_data['open'].iloc[-1]}")
    print(f"  收盘价: {daily_data['close'].iloc[-1]}")
    print(f"  最高价: {daily_data['high'].iloc[-1]}")
    print(f"  最低价: {daily_data['low'].iloc[-1]}")
    
    # 估算分钟级走势
    vector = loader.estimate_minute_from_daily(daily_data)
    
    print(f"\n【估算的240维向量】")
    print(f"  向量长度: {len(vector)}")
    print(f"  起始值: {vector[0]:.2f}% (开盘)")
    print(f"  结束值: {vector[-1]:.2f}% (收盘)")
    print(f"  最高点: {np.max(vector):.2f}%")
    print(f"  最低点: {np.min(vector):.2f}%")
    
    # 用估算的向量进行形态分析
    result = analyzer.analyze_single_stock(pd.DataFrame({'close': vector + 100}))
    print(f"\n【估算走势的形态识别】")
    print(f"  形态: {result['pattern_name']}")


def main():
    args = parse_args()
    
    print("=" * 60)
    print("分钟级走势形态分析 - 全新方法演示")
    print("核心思想：240维向量，每分钟一个采样点")
    print("=" * 60)
    
    if args.pattern == "all":
        demo_single_stock()
        demo_v_shape()
        demo_consolidation()
        demo_compare()
        demo_estimate_from_daily()
    elif args.pattern == "single":
        demo_single_stock()
    elif args.pattern == "v_shape":
        demo_v_shape()
    elif args.pattern == "consolidation":
        demo_consolidation()
    elif args.pattern == "compare":
        demo_compare()
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
    print("\n下一步：")
    print("  1. 结合真实分钟级数据进行分析")
    print("  2. 使用机器学习模型识别形态")
    print("  3. 对比不同股票的走势相似度")
    print("  4. 发现潜在的股票联动效应")


if __name__ == "__main__":
    main()
