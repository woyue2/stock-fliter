# -*- coding: utf-8 -*-
"""
市场情绪分析 - 高开低走/低开高走检测

功能：
- 分析市场整体股票的高开低走和低开高走情况
- 统计早盘、午盘不同时间段的市场情绪
- 生成市场情绪报告

运行模式：
- python main.py --date 2026-01-30  # 分析指定日期
- python main.py --recent 5         # 分析最近5个交易日
- python main.py                    # 分析最新交易日
"""
import argparse
import sys
from datetime import datetime, timedelta
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

from data_loader import MarketDataLoader
from analyzer import MarketSentimentAnalyzer
from reporter import MarketSentimentReporter


def parse_args():
    parser = argparse.ArgumentParser(
        description="市场情绪分析 - 高开低走/低开高走检测",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python main.py                    # 分析最新交易日
  python main.py --date 2026-01-30  # 分析指定日期
  python main.py --recent 5         # 分析最近5个交易日
  python main.py --all              # 分析所有可用数据（慎用）
        """
    )
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--date", "-d",
        type=str,
        help="指定分析日期 (格式: YYYY-MM-DD)"
    )
    group.add_argument(
        "--recent", "-r",
        type=int,
        help="分析最近N个交易日"
    )
    group.add_argument(
        "--all", "-a",
        action="store_true",
        help="分析所有可用数据"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output",
        help="输出目录 (默认: output)"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["html", "csv", "both"],
        default="both",
        help="输出格式 (默认: both)"
    )
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    # 初始化组件
    base_dir = Path(__file__).resolve().parent
    stocks_index_dir = base_dir.parent / "get-data" / "data" / "stocks_index"
    output_dir = base_dir / args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("市场情绪分析 - 高开低走/低开高走检测")
    print("=" * 60)
    
    # 加载数据
    print("\n[1/3] 加载数据...")
    loader = MarketDataLoader(stocks_index_dir)
    
    # 显示可用日期
    available_dates = loader.get_available_dates()
    if available_dates:
        print(f"[信息] 可用数据日期: {available_dates[0]} 至 {available_dates[-1]} (共 {len(available_dates)} 天)")
    
    if args.date:
        # 分析指定日期
        target_date = args.date
        print(f"分析日期: {target_date}")
        market_data = loader.load_single_date(target_date, show_progress=True)
        if market_data.empty:
            print(f"错误: 没有找到 {target_date} 的数据")
            return 1
    elif args.recent:
        # 分析最近N天
        print(f"分析最近 {args.recent} 个交易日")
        market_data = loader.load_recent_days(args.recent, show_progress=True)
        if market_data.empty:
            print(f"错误: 没有找到最近 {args.recent} 天的数据")
            return 1
    elif args.all:
        # 分析所有数据
        print("分析所有可用数据...")
        market_data = loader.load_all_data(show_progress=True)
        if market_data.empty:
            print("错误: 没有找到任何数据")
            return 1
    else:
        # 默认：分析最近2天（需要前一日数据来计算涨跌幅）
        print("分析最新交易日（加载最近2天数据以计算涨跌幅）")
        market_data = loader.load_recent_days(2, show_progress=True)
        if market_data.empty:
            print("错误: 没有找到最新数据")
            return 1
    
    print(f"[OK] 加载完成: {len(market_data)} 条记录")
    
    # 计算前一日收盘价（用于计算涨跌幅）
    print("\n[2/4] 计算前一日收盘价...")
    market_data = loader.calculate_previous_close(market_data)
    
    # 过滤掉没有前一日收盘价的记录
    valid_count = len(market_data[market_data['prev_close'].notna()])
    print(f"[OK] 有效记录: {valid_count} 条")
    
    # 分析数据
    print("\n[3/4] 分析市场情绪...")
    analyzer = MarketSentimentAnalyzer()
    analysis_result = analyzer.analyze(market_data)
    
    if not analysis_result:
        print("错误: 分析失败")
        return 1
    
    print(f"[OK] 分析完成")
    
    # 生成报告
    print("\n[4/4] 生成报告...")
    reporter = MarketSentimentReporter(output_dir)
    
    report_files = []
    if args.format in ["html", "both"]:
        html_file = reporter.generate_html_report(analysis_result)
        report_files.append(html_file)
        print(f"[OK] HTML报告: {html_file}")
    
    if args.format in ["csv", "both"]:
        csv_file = reporter.generate_csv_report(analysis_result)
        report_files.append(csv_file)
        print(f"[OK] CSV报告: {csv_file}")
    
    print("\n" + "=" * 60)
    print("分析完成！")
    print("=" * 60)
    
    # 显示简要统计
    if "summary" in analysis_result:
        summary = analysis_result["summary"]
        print(f"\n[统计] 市场概况:")
        print(f"  总股票数: {summary.get('total_stocks', 0)}")
        print(f"  高开低走: {summary.get('high_open_low_close_count', 0)} ({summary.get('high_open_low_close_pct', 0):.1f}%)")
        print(f"  低开高走: {summary.get('low_open_high_close_count', 0)} ({summary.get('low_open_high_close_pct', 0):.1f}%)")
        print(f"  市场情绪指数: {summary.get('sentiment_index', 0):.2f}")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

