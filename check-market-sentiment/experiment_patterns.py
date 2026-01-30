# -*- coding: utf-8 -*-
"""
经典走势形态实验

测试和验证各种经典走势形态的识别效果
"""
import sys
from pathlib import Path
from datetime import datetime

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

from data_loader import MarketDataLoader
from pattern_analyzer import PatternAnalyzer
from pattern_html_reporter import PatternHTMLReporter
import pandas as pd


def print_section(title: str):
    """打印分节标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def experiment_1_basic_patterns():
    """实验1：基础形态识别"""
    print_section("实验1：基础形态识别")
    
    # 加载数据
    base_dir = Path(__file__).resolve().parent
    stocks_index_dir = base_dir.parent / "get-data" / "data" / "stocks_index"
    
    print("\n[步骤1] 加载最新交易日数据...")
    loader = MarketDataLoader(stocks_index_dir)
    market_data = loader.load_recent_days(1, show_progress=True)
    
    if market_data.empty:
        print("错误: 没有数据")
        return
    
    # 计算前一日收盘价
    print("\n[步骤2] 计算前一日收盘价...")
    market_data = loader.calculate_previous_close(market_data)
    market_data = market_data[market_data['prev_close'].notna()]
    print(f"有效数据: {len(market_data)} 条")
    
    # 分析形态
    print("\n[步骤3] 分析走势形态...")
    analyzer = PatternAnalyzer()
    result = analyzer.analyze_market(market_data)
    
    # 生成报告
    print("\n[步骤4] 生成分析报告...")
    report = analyzer.generate_pattern_report(result)
    print("\n" + report)
    
    return result


def experiment_2_pattern_examples():
    """实验2：各形态的典型案例"""
    print_section("实验2：各形态的典型案例")
    
    # 加载数据
    base_dir = Path(__file__).resolve().parent
    stocks_index_dir = base_dir.parent / "get-data" / "data" / "stocks_index"
    
    print("\n加载数据...")
    loader = MarketDataLoader(stocks_index_dir)
    market_data = loader.load_recent_days(1, show_progress=False)
    market_data = loader.calculate_previous_close(market_data)
    market_data = market_data[market_data['prev_close'].notna()]
    
    # 分析形态
    analyzer = PatternAnalyzer()
    result = analyzer.analyze_market(market_data)
    df = result['data']
    
    # 显示每种形态的典型案例
    pattern_types = df['pattern_name'].unique()
    
    for pattern_name in sorted(pattern_types):
        print(f"\n{'─' * 70}")
        print(f"【{pattern_name}】")
        print(f"{'─' * 70}")
        
        # 获取该形态的股票
        pattern_stocks = df[df['pattern_name'] == pattern_name]
        
        # 按振幅排序，取前3个最典型的
        pattern_stocks = pattern_stocks.sort_values('amplitude', ascending=False).head(3)
        
        for idx, row in pattern_stocks.iterrows():
            print(f"\n  股票: {row['code']} {row.get('name', 'N/A')}")
            print(f"  开盘涨跌: {row['open_change_pct']:>6.2f}%  (开盘相对昨收)")
            print(f"  日内涨跌: {row['intraday_change_pct']:>6.2f}%  (收盘相对开盘)")
            print(f"  全天涨跌: {row['total_change_pct']:>6.2f}%  (收盘相对昨收)")
            print(f"  振幅:     {row['amplitude']:>6.2f}%")
            print(f"  上影线:   {row['upper_shadow_ratio']:>6.2f}%")
            print(f"  下影线:   {row['lower_shadow_ratio']:>6.2f}%")
            print(f"  实体:     {row['body_ratio']:>6.2f}%")
    
    return result


def experiment_3_sentiment_analysis():
    """实验3：市场情绪分析"""
    print_section("实验3：市场情绪分析")
    
    # 加载最近5天数据
    base_dir = Path(__file__).resolve().parent
    stocks_index_dir = base_dir.parent / "get-data" / "data" / "stocks_index"
    
    print("\n加载最近5个交易日数据...")
    loader = MarketDataLoader(stocks_index_dir)
    market_data = loader.load_recent_days(5, show_progress=True)
    
    if market_data.empty:
        print("错误: 没有数据")
        return
    
    market_data = loader.calculate_previous_close(market_data)
    market_data = market_data[market_data['prev_close'].notna()]
    
    # 按日期分组分析
    analyzer = PatternAnalyzer()
    
    print("\n每日市场情绪变化:")
    print(f"{'─' * 70}")
    print(f"{'日期':<12} {'总数':>6} {'强势':>6} {'弱势':>6} {'情绪指数':>8} {'平均涨跌':>8}")
    print(f"{'─' * 70}")
    
    dates = sorted(market_data['date'].unique())
    
    for date in dates:
        daily_data = market_data[market_data['date'] == date]
        result = analyzer.analyze_market(daily_data)
        
        date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
        
        print(f"{date_str:<12} "
              f"{result['total_stocks']:>6} "
              f"{result['bullish_count']:>6} "
              f"{result['bearish_count']:>6} "
              f"{result['sentiment_index']:>8.2f} "
              f"{result['avg_metrics']['avg_total_change']:>8.2f}%")
    
    print(f"{'─' * 70}")


def experiment_4_extreme_patterns():
    """实验4：极端形态识别"""
    print_section("实验4：极端形态识别")
    
    # 加载数据
    base_dir = Path(__file__).resolve().parent
    stocks_index_dir = base_dir.parent / "get-data" / "data" / "stocks_index"
    
    print("\n加载数据...")
    loader = MarketDataLoader(stocks_index_dir)
    market_data = loader.load_recent_days(1, show_progress=False)
    market_data = loader.calculate_previous_close(market_data)
    market_data = market_data[market_data['prev_close'].notna()]
    
    # 分析形态
    analyzer = PatternAnalyzer()
    result = analyzer.analyze_market(market_data)
    df = result['data']
    
    print("\n【极端形态 TOP 10】")
    
    # 1. 最强的高开低走（冲高回落最厉害）
    print(f"\n{'─' * 70}")
    print("1. 最强高开低走 (先上升再下降，整体往下走)")
    print(f"{'─' * 70}")
    high_open_low_close = df[df['pattern_name'].str.contains('高开低走')]
    if not high_open_low_close.empty:
        # 按开盘涨幅和日内跌幅的差值排序
        high_open_low_close['pattern_strength'] = high_open_low_close['open_change_pct'] - high_open_low_close['intraday_change_pct']
        top_holc = high_open_low_close.nlargest(5, 'pattern_strength')
        
        for idx, row in top_holc.iterrows():
            print(f"\n  {row['code']} {row.get('name', 'N/A')}")
            print(f"    开盘: +{row['open_change_pct']:.2f}% → 日内: {row['intraday_change_pct']:.2f}% → 全天: {row['total_change_pct']:.2f}%")
            print(f"    形态强度: {row['pattern_strength']:.2f}  (开盘涨幅 - 日内跌幅)")
    
    # 2. 最强的低开高走（探底反弹最厉害）
    print(f"\n{'─' * 70}")
    print("2. 最强低开高走 (先下降再上升，整体往上走)")
    print(f"{'─' * 70}")
    low_open_high_close = df[df['pattern_name'].str.contains('低开高走')]
    if not low_open_high_close.empty:
        # 按日内涨幅和开盘跌幅的差值排序
        low_open_high_close['pattern_strength'] = low_open_high_close['intraday_change_pct'] - low_open_high_close['open_change_pct']
        top_lohc = low_open_high_close.nlargest(5, 'pattern_strength')
        
        for idx, row in top_lohc.iterrows():
            print(f"\n  {row['code']} {row.get('name', 'N/A')}")
            print(f"    开盘: {row['open_change_pct']:.2f}% → 日内: +{row['intraday_change_pct']:.2f}% → 全天: {row['total_change_pct']:.2f}%")
            print(f"    形态强度: {row['pattern_strength']:.2f}  (日内涨幅 - 开盘跌幅)")
    
    # 3. 最强V型反转
    print(f"\n{'─' * 70}")
    print("3. 最强V型反转")
    print(f"{'─' * 70}")
    v_reversal = df[df['pattern_name'] == 'V型反转']
    if not v_reversal.empty:
        top_v = v_reversal.nlargest(5, 'intraday_change_pct')
        
        for idx, row in top_v.iterrows():
            print(f"\n  {row['code']} {row.get('name', 'N/A')}")
            print(f"    开盘: {row['open_change_pct']:.2f}% → 日内: +{row['intraday_change_pct']:.2f}% → 全天: {row['total_change_pct']:.2f}%")
            print(f"    下影线: {row['lower_shadow_ratio']:.2f}%")
    
    # 4. 最强倒V型
    print(f"\n{'─' * 70}")
    print("4. 最强倒V型")
    print(f"{'─' * 70}")
    inverted_v = df[df['pattern_name'] == '倒V型']
    if not inverted_v.empty:
        top_inv_v = inverted_v.nsmallest(5, 'intraday_change_pct')
        
        for idx, row in top_inv_v.iterrows():
            print(f"\n  {row['code']} {row.get('name', 'N/A')}")
            print(f"    开盘: +{row['open_change_pct']:.2f}% → 日内: {row['intraday_change_pct']:.2f}% → 全天: {row['total_change_pct']:.2f}%")
            print(f"    上影线: {row['upper_shadow_ratio']:.2f}%")
    
    # 5. 最强单边上涨
    print(f"\n{'─' * 70}")
    print("5. 最强单边上涨")
    print(f"{'─' * 70}")
    strong_up = df[df['pattern_name'] == '单边上涨']
    if not strong_up.empty:
        top_up = strong_up.nlargest(5, 'total_change_pct')
        
        for idx, row in top_up.iterrows():
            print(f"\n  {row['code']} {row.get('name', 'N/A')}")
            print(f"    开盘: +{row['open_change_pct']:.2f}% → 日内: +{row['intraday_change_pct']:.2f}% → 全天: +{row['total_change_pct']:.2f}%")
    
    # 6. 最强单边下跌
    print(f"\n{'─' * 70}")
    print("6. 最强单边下跌")
    print(f"{'─' * 70}")
    strong_down = df[df['pattern_name'] == '单边下跌']
    if not strong_down.empty:
        top_down = strong_down.nsmallest(5, 'total_change_pct')
        
        for idx, row in top_down.iterrows():
            print(f"\n  {row['code']} {row.get('name', 'N/A')}")
            print(f"    开盘: {row['open_change_pct']:.2f}% → 日内: {row['intraday_change_pct']:.2f}% → 全天: {row['total_change_pct']:.2f}%")


def experiment_5_export_results():
    """实验5：导出详细结果"""
    print_section("实验5：导出详细结果")
    
    # 加载数据
    base_dir = Path(__file__).resolve().parent
    stocks_index_dir = base_dir.parent / "get-data" / "data" / "stocks_index"
    output_dir = base_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    print("\n加载数据...")
    loader = MarketDataLoader(stocks_index_dir)
    market_data = loader.load_recent_days(1, show_progress=False)
    market_data = loader.calculate_previous_close(market_data)
    market_data = market_data[market_data['prev_close'].notna()]
    
    # 分析形态
    print("分析形态...")
    analyzer = PatternAnalyzer()
    result = analyzer.analyze_market(market_data)
    df = result['data']
    
    # 导出CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = output_dir / f"pattern_analysis_{timestamp}.csv"
    
    # 选择要导出的列
    export_cols = [
        'code', 'name', 'date', 'open', 'close', 'high', 'low', 'prev_close',
        'pattern_name', 'open_change_pct', 'intraday_change_pct', 'total_change_pct',
        'amplitude', 'upper_shadow_ratio', 'lower_shadow_ratio', 'body_ratio'
    ]
    
    # 只导出存在的列
    export_cols = [col for col in export_cols if col in df.columns]
    
    df[export_cols].to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"\n✓ 已导出CSV文件: {csv_file}")
    print(f"  总记录数: {len(df)}")
    
    # 生成统计报告
    report_file = output_dir / f"pattern_report_{timestamp}.txt"
    report = analyzer.generate_pattern_report(result)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✓ 已导出报告文件: {report_file}")
    
    # 生成HTML报告
    print("生成HTML报告...")
    html_reporter = PatternHTMLReporter(output_dir)
    html_file = html_reporter.generate_report(result)
    print(f"✓ 已导出HTML报告: {html_file}")
    
    return csv_file, report_file, html_file


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("  经典走势形态实验")
    print("=" * 70)
    print("\n本实验将识别以下几种经典形态：")
    print("  1. 高开低走型 - 先上升再下降，整体往下走")
    print("  2. 低开高走型 - 先下降再上升，整体往上走")
    print("  3. V型反转 - 低开后强势反弹")
    print("  4. 倒V型 - 高开后大幅回落")
    print("  5. 单边上涨 - 持续走强")
    print("  6. 单边下跌 - 持续走弱")
    print("  7. 震荡整理 - 上下波动")
    print("  8. 平淡走势 - 几乎无波动")
    
    try:
        # 运行实验
        experiment_1_basic_patterns()
        experiment_2_pattern_examples()
        experiment_3_sentiment_analysis()
        experiment_4_extreme_patterns()
        experiment_5_export_results()
        
        print("\n" + "=" * 70)
        print("  实验完成！")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

