# -*- coding: utf-8 -*-
"""
运行选股扫描
支持全市场扫描和自定义股票池
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from stock_scanner import StockScanner


def scan_full_market(min_signals=2):
    """
    扫描全市场

    Parameters:
    -----------
    min_signals : int
        最少信号数量（默认2）
    """
    print("\n" + "="*60)
    print("全市场选股扫描")
    print("="*60 + "\n")

    scanner = StockScanner(
        output_dir='./output',
        data_dir='./data'
    )

    # 扫描全市场
    qualified, all_results = scanner.scan_stock_list(
        stock_list=None,  # None表示全市场
        min_signals=min_signals,
        save_results=True
    )

    # 生成报告
    scanner.generate_report(qualified, all_results)

    return qualified, all_results


def scan_custom_stocks(stock_codes, min_signals=1):
    """
    扫描自定义股票列表

    Parameters:
    -----------
    stock_codes : list
        股票代码列表，如 ['000001', '000002', '600000']
    min_signals : int
        最少信号数量
    """
    print("\n" + "="*60)
    print("自定义股票池扫描")
    print("="*60 + "\n")

    scanner = StockScanner(
        output_dir='./output',
        data_dir='./data'
    )

    # 扫描自定义列表
    qualified, all_results = scanner.scan_stock_list(
        stock_list=stock_codes,
        min_signals=min_signals,
        save_results=True
    )

    # 生成报告
    scanner.generate_report(qualified, all_results)

    return qualified, all_results


def scan_top_stocks(n=300, min_signals=2):
    """
    扫描前N只股票（用于快速测试）

    Parameters:
    -----------
    n : int
        扫描股票数量
    min_signals : int
        最少信号数量
    """
    print("\n" + "="*60)
    print(f"快速测试 - 扫描前 {n} 只股票")
    print("="*60 + "\n")

    scanner = StockScanner(
        output_dir='./output',
        data_dir='./data'
    )

    # 获取全市场列表（包含名称）
    print("正在获取股票列表...")
    all_stocks_dict = scanner.data_fetcher.get_stock_list()

    # 取前N只（保持字典格式）
    stock_codes = list(all_stocks_dict.keys())[:n]
    test_stocks = {code: all_stocks_dict[code] for code in stock_codes}

    # 扫描
    qualified, all_results = scanner.scan_stock_list(
        stock_list=test_stocks,
        min_signals=min_signals,
        save_results=True
    )

    # 生成报告
    scanner.generate_report(qualified, all_results)

    return qualified, all_results


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='选股扫描器')
    parser.add_argument('--mode', type=str, default='test',
                        choices=['full', 'test', 'custom'],
                        help='扫描模式: full=全市场, test=测试前N只, custom=自定义列表')
    parser.add_argument('--n', type=int, default=300,
                        help='测试模式下扫描的股票数量')
    parser.add_argument('--min-signals', type=int, default=2,
                        help='最少信号数量')
    parser.add_argument('--stocks', type=str, nargs='+',
                        help='自定义股票代码列表 (如: 000001 000002 600000)')

    args = parser.parse_args()

    if args.mode == 'full':
        # 全市场扫描
        scan_full_market(min_signals=args.min_signals)

    elif args.mode == 'test':
        # 测试模式 - 扫描前N只
        scan_top_stocks(n=args.n, min_signals=args.min_signals)

    elif args.mode == 'custom':
        # 自定义列表
        if not args.stocks:
            print("✗ 自定义模式需要提供股票代码列表")
            print("  使用示例: python run_scan.py --mode custom --stocks 000001 000002 600000")
        else:
            scan_custom_stocks(args.stocks, min_signals=args.min_signals)
