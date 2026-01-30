# -*- coding: utf-8 -*-
"""
分析 2025-05-06 的股票走势形态
（注意：2025-05-05是假期，无交易数据）
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


def main():
    """分析 2025-05-06 的股票走势"""
    print("=" * 70)
    print("  分析 2025-05-06 股票走势形态")
    print("  (stocks_index/2025-05-05 中的股票)")
    print("=" * 70)
    
    # 设置路径
    base_dir = Path(__file__).resolve().parent
    stocks_index_dir = base_dir.parent / "get-data" / "data" / "stocks_index"
    output_dir = base_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # 注意：2025-05-05没有交易数据（五一假期），使用2025-05-06
    target_date = "2025-05-06"
    
    try:
        # 1. 加载数据
        print(f"\n[1/5] 加载 {target_date} 的数据...")
        print("  注意：2025-05-05是假期，分析2025-05-06的数据")
        loader = MarketDataLoader(stocks_index_dir)
        
        # 加载2天数据（需要前一日收盘价）
        print("  加载2天数据以计算前一日收盘价...")
        market_data = loader.load_date_range("2025-02-05", "2025-05-06", show_progress=True)
        
        if market_data.empty:
            print(f"错误: 没有找到 {target_date} 的数据")
            return 1
        
        print(f"  总记录数: {len(market_data)}")
        
        # 2. 计算前一日收盘价
        print("\n[2/5] 计算前一日收盘价...")
        market_data = loader.calculate_previous_close(market_data)
        
        # 只保留目标日期的数据
        market_data['date'] = pd.to_datetime(market_data['date'])
        target_dt = pd.to_datetime(target_date)
        market_data = market_data[market_data['date'] == target_dt]
        
        # 过滤有效数据
        valid_data = market_data[market_data['prev_close'].notna()].copy()
        print(f"  有效记录数: {len(valid_data)}")
        
        if valid_data.empty:
            print("错误: 没有有效数据")
            return 1
        
        # 3. 分析形态
        print("\n[3/5] 分析走势形态...")
        analyzer = PatternAnalyzer()
        result = analyzer.analyze_market(valid_data)
        
        # 4. 生成报告
        print("\n[4/5] 生成统计报告...")
        report = analyzer.generate_pattern_report(result)
        print("\n" + report)
        
        # 5. 导出结果
        print("\n[5/5] 导出结果...")
        
        # 导出CSV
        csv_file = output_dir / f"pattern_analysis_20250506.csv"
        df = result['data']
        export_cols = [
            'code', 'name', 'date', 'open', 'close', 'high', 'low', 'prev_close',
            'pattern_name', 'open_change_pct', 'intraday_change_pct', 'total_change_pct',
            'amplitude', 'upper_shadow_ratio', 'lower_shadow_ratio', 'body_ratio'
        ]
        export_cols = [col for col in export_cols if col in df.columns]
        df[export_cols].to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"✓ CSV文件: {csv_file}")
        
        # 导出TXT报告
        txt_file = output_dir / f"pattern_report_20250506.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✓ TXT报告: {txt_file}")
        
        # 生成HTML报告
        html_reporter = PatternHTMLReporter(output_dir)
        html_file = html_reporter.generate_report(result, target_date)
        print(f"✓ HTML报告: {html_file}")
        
        # 显示一些典型案例
        print("\n" + "=" * 70)
        print("  典型形态案例")
        print("=" * 70)
        
        # 高开低走
        high_low = df[df['pattern_name'].str.contains('高开低走')]
        if not high_low.empty:
            print(f"\n【高开低走型】共 {len(high_low)} 只")
            top5 = high_low.nlargest(5, 'open_change_pct')
            for idx, row in top5.iterrows():
                print(f"  {row['code']} {row.get('name', 'N/A')}")
                print(f"    开盘: {row['open_change_pct']:+.2f}% → 日内: {row['intraday_change_pct']:+.2f}% → 全天: {row['total_change_pct']:+.2f}%")
        
        # 低开高走
        low_high = df[df['pattern_name'].str.contains('低开高走')]
        if not low_high.empty:
            print(f"\n【低开高走型】共 {len(low_high)} 只")
            top5 = low_high.nlargest(5, 'intraday_change_pct')
            for idx, row in top5.iterrows():
                print(f"  {row['code']} {row.get('name', 'N/A')}")
                print(f"    开盘: {row['open_change_pct']:+.2f}% → 日内: {row['intraday_change_pct']:+.2f}% → 全天: {row['total_change_pct']:+.2f}%")
        
        # V型反转
        v_reversal = df[df['pattern_name'] == 'V型反转']
        if not v_reversal.empty:
            print(f"\n【V型反转】共 {len(v_reversal)} 只")
            for idx, row in v_reversal.head(5).iterrows():
                print(f"  {row['code']} {row.get('name', 'N/A')}")
                print(f"    开盘: {row['open_change_pct']:+.2f}% → 日内: {row['intraday_change_pct']:+.2f}% → 全天: {row['total_change_pct']:+.2f}%")
        
        # 单边上涨
        strong_up = df[df['pattern_name'] == '单边上涨']
        if not strong_up.empty:
            print(f"\n【单边上涨】共 {len(strong_up)} 只")
            top5 = strong_up.nlargest(5, 'total_change_pct')
            for idx, row in top5.iterrows():
                print(f"  {row['code']} {row.get('name', 'N/A')}")
                print(f"    开盘: {row['open_change_pct']:+.2f}% → 日内: {row['intraday_change_pct']:+.2f}% → 全天: {row['total_change_pct']:+.2f}%")
        
        print("\n" + "=" * 70)
        print("  分析完成！")
        print("=" * 70)
        print(f"\n请用浏览器打开HTML报告查看完整分析结果：")
        print(f"{html_file}")
        
        return 0
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

