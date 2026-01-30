# -*- coding: utf-8 -*-
"""
快速测试 - 验证形态识别功能
"""
import sys
from pathlib import Path

# 设置UTF-8输出
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 添加父目录到路径
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from pattern_analyzer import PatternAnalyzer
import pandas as pd


def test_pattern_recognition():
    """测试形态识别功能"""
    print("=" * 60)
    print("  形态识别功能测试")
    print("=" * 60)
    
    # 创建测试数据
    test_cases = [
        {
            'name': '高开低走案例',
            'prev_close': 10.0,
            'open': 10.5,   # +5%
            'close': 10.2,  # -2.86% from open
            'high': 10.6,
            'low': 10.1,
            'expected': '高开低走'
        },
        {
            'name': '低开高走案例',
            'prev_close': 10.0,
            'open': 9.5,    # -5%
            'close': 9.8,   # +3.16% from open
            'high': 9.9,
            'low': 9.4,
            'expected': '低开高走'
        },
        {
            'name': 'V型反转案例',
            'prev_close': 10.0,
            'open': 9.5,    # -5%
            'close': 10.2,  # +7.37% from open
            'high': 10.3,
            'low': 9.3,     # 长下影线
            'expected': 'V型反转'
        },
        {
            'name': '倒V型案例',
            'prev_close': 10.0,
            'open': 10.5,   # +5%
            'close': 10.0,  # -4.76% from open
            'high': 10.8,   # 长上影线
            'low': 9.9,
            'expected': '倒V型'
        },
        {
            'name': '单边上涨案例',
            'prev_close': 10.0,
            'open': 10.3,   # +3%
            'close': 10.8,  # +4.85% from open
            'high': 10.9,
            'low': 10.2,
            'expected': '单边上涨'
        },
        {
            'name': '单边下跌案例',
            'prev_close': 10.0,
            'open': 9.7,    # -3%
            'close': 9.2,   # -5.15% from open
            'high': 9.8,
            'low': 9.1,
            'expected': '单边下跌'
        },
    ]
    
    # 创建分析器
    analyzer = PatternAnalyzer()
    
    print("\n测试用例：\n")
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        print(f"{'─' * 60}")
        print(f"测试 {i}: {case['name']}")
        print(f"{'─' * 60}")
        
        # 创建数据行
        row = pd.Series({
            'open': case['open'],
            'close': case['close'],
            'high': case['high'],
            'low': case['low'],
            'prev_close': case['prev_close']
        })
        
        # 分析形态
        pattern_code, pattern_name, metrics = analyzer.analyze_pattern(row)
        
        # 显示结果
        print(f"昨收: {case['prev_close']:.2f}")
        print(f"开盘: {case['open']:.2f}  (开盘涨跌: {metrics['open_change_pct']:+.2f}%)")
        print(f"收盘: {case['close']:.2f}  (日内涨跌: {metrics['intraday_change_pct']:+.2f}%)")
        print(f"最高: {case['high']:.2f}")
        print(f"最低: {case['low']:.2f}")
        print(f"全天涨跌: {metrics['total_change_pct']:+.2f}%")
        print(f"振幅: {metrics['amplitude']:.2f}%")
        print(f"\n识别结果: {pattern_name}")
        print(f"期望结果: {case['expected']}")
        
        # 检查是否匹配
        if case['expected'] in pattern_name:
            print("✓ 测试通过")
            passed += 1
        else:
            print("✗ 测试失败")
            failed += 1
        
        print()
    
    # 总结
    print("=" * 60)
    print(f"测试总结: 通过 {passed}/{len(test_cases)}, 失败 {failed}/{len(test_cases)}")
    print("=" * 60)
    
    return passed == len(test_cases)


def test_market_analysis():
    """测试市场分析功能"""
    print("\n" + "=" * 60)
    print("  市场分析功能测试")
    print("=" * 60)
    
    # 创建模拟市场数据
    data = []
    for i in range(100):
        # 随机生成不同形态的股票
        import random
        prev_close = 10.0
        
        # 随机选择形态类型
        pattern_type = random.choice(['high_low', 'low_high', 'up', 'down', 'flat'])
        
        if pattern_type == 'high_low':
            open_price = prev_close * (1 + random.uniform(0.01, 0.05))
            close_price = open_price * (1 - random.uniform(0.01, 0.03))
        elif pattern_type == 'low_high':
            open_price = prev_close * (1 - random.uniform(0.01, 0.05))
            close_price = open_price * (1 + random.uniform(0.01, 0.03))
        elif pattern_type == 'up':
            open_price = prev_close * (1 + random.uniform(0.01, 0.03))
            close_price = open_price * (1 + random.uniform(0.01, 0.03))
        elif pattern_type == 'down':
            open_price = prev_close * (1 - random.uniform(0.01, 0.03))
            close_price = open_price * (1 - random.uniform(0.01, 0.03))
        else:
            open_price = prev_close * (1 + random.uniform(-0.005, 0.005))
            close_price = open_price * (1 + random.uniform(-0.005, 0.005))
        
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.02))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.02))
        
        data.append({
            'code': f'{i:06d}',
            'name': f'股票{i}',
            'open': open_price,
            'close': close_price,
            'high': high_price,
            'low': low_price,
            'prev_close': prev_close
        })
    
    df = pd.DataFrame(data)
    
    # 分析市场
    analyzer = PatternAnalyzer()
    result = analyzer.analyze_market(df)
    
    # 显示结果
    print(f"\n总股票数: {result['total_stocks']}")
    print(f"强势形态: {result['bullish_count']} ({result['bullish_count']/result['total_stocks']*100:.1f}%)")
    print(f"弱势形态: {result['bearish_count']} ({result['bearish_count']/result['total_stocks']*100:.1f}%)")
    print(f"市场情绪指数: {result['sentiment_index']:.2f}")
    
    print("\n形态分布:")
    for pattern_name, count in sorted(result['pattern_counts'].items(), key=lambda x: x[1], reverse=True):
        pct = result['pattern_percentages'][pattern_name]
        print(f"  {pattern_name}: {count} ({pct:.1f}%)")
    
    print("\n✓ 市场分析功能正常")
    
    return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  经典走势形态识别 - 功能测试")
    print("=" * 60)
    print()
    
    try:
        # 测试1：形态识别
        test1_passed = test_pattern_recognition()
        
        # 测试2：市场分析
        test2_passed = test_market_analysis()
        
        # 总结
        print("\n" + "=" * 60)
        if test1_passed and test2_passed:
            print("  ✓ 所有测试通过！")
            print("  可以运行 experiment_patterns.py 进行完整实验")
        else:
            print("  ✗ 部分测试失败")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

