# -*- coding: utf-8 -*-
"""
TD序列扫描器
专门分析日K、周K、月K的TD序列（9底、8底、7底）
"""
import sys
import io
import os
import time
import pandas as pd
from datetime import datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from data_fetcher import DataFetcher
from technical_indicators import TechnicalIndicators


class TDScanner:
    """TD序列扫描器"""

    def __init__(self, data_dir='./data', output_dir='./output'):
        """
        初始化扫描器

        Parameters:
        -----------
        data_dir : str
            数据目录
        output_dir : str
            输出目录
        """
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.data_fetcher = DataFetcher(data_dir=data_dir)
        self.indicators = TechnicalIndicators()

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

    def scan_stock_td(self, stock_code, stock_name='', periods=['daily', 'weekly', 'monthly']):
        """
        扫描单只股票的TD序列

        Parameters:
        -----------
        stock_code : str
            股票代码
        stock_name : str
            股票名称
        periods : list
            要分析的周期列表：'daily'(日K), 'weekly'(周K), 'monthly'(月K)

        Returns:
        --------
        dict or None
            扫描结果
        """
        result = {
            'code': stock_code,
            'name': stock_name,
            'daily': None,
            'weekly': None,
            'monthly': None
        }

        # 扫描各个周期
        for period in periods:
            # 获取数据
            if period == 'daily':
                df = self.data_fetcher.get_stock_data(
                    stock_code,
                    period='daily',
                    start_date='20200101',
                    save_to_file=False  # 不保存文件，避免过多文件
                )
            elif period == 'weekly':
                df = self.data_fetcher.get_stock_data(
                    stock_code,
                    period='weekly',
                    start_date='20200101',
                    save_to_file=False
                )
            elif period == 'monthly':
                df = self.data_fetcher.get_stock_data(
                    stock_code,
                    period='monthly',
                    start_date='20200101',
                    save_to_file=False
                )
            else:
                continue

            if df is None or len(df) < 10:
                continue

            # 计算TD序列
            close_prices = df['close']
            td_result = self.indicators.calculate_td_sequence(close_prices)

            # 保存该周期的结果
            result[period] = {
                'date': df['date'].iloc[-1].strftime('%Y-%m-%d'),
                'close': round(df['close'].iloc[-1], 2),
                'td_count': td_result['current_buy'],
                'td_9': td_result['is_buy_setup'],
                'td_8': td_result['is_buy_setup_8'],
                'td_7': td_result['is_buy_setup_7']
            }

        return result

    def scan_stock_list(self, stock_list=None, periods=['daily', 'weekly', 'monthly'],
                       min_td_count=7, save_results=True):
        """
        扫描股票列表

        Parameters:
        -----------
        stock_list : list or dict or None
            股票代码列表 或 {代码: 名称}字典，None表示全市场
        periods : list
            要分析的周期列表
        min_td_count : int
            最小TD计数（默认7，即包含7底及以上）
        save_results : bool
            是否保存结果

        Returns:
        --------
        tuple
            (符合条件股票列表, 所有扫描结果)
        """
        # 如果没有提供股票列表，获取全市场
        if stock_list is None:
            print("正在获取股票列表...")
            stock_list = self.data_fetcher.get_stock_list()

        if not stock_list:
            print("✗ 股票列表为空")
            return [], []

        # 处理输入格式：支持list或dict
        if isinstance(stock_list, dict):
            stock_dict = stock_list
            stock_codes = list(stock_dict.keys())
        else:
            stock_dict = {code: '' for code in stock_list}
            stock_codes = stock_list

        period_names = {
            'daily': '日K',
            'weekly': '周K',
            'monthly': '月K'
        }
        period_str = '、'.join([period_names.get(p, p) for p in periods])

        print(f"\n开始扫描 {len(stock_codes)} 只股票的 {period_str} TD序列...")
        print(f"筛选条件: TD计数 ≥ {min_td_count}\n")

        all_results = []
        qualified_stocks = []

        start_time = time.time()
        last_progress_time = start_time

        for i, stock_code in enumerate(stock_codes):
            # 进度显示（每50只或每2秒更新一次）
            current_time = time.time()
            if (i + 1) % 50 == 0 or (i + 1) == len(stock_codes) or (current_time - last_progress_time) >= 2:
                elapsed = current_time - start_time
                progress = (i + 1) / len(stock_codes) * 100
                speed = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (len(stock_codes) - i - 1) / speed if speed > 0 else 0
                print(f"[{i + 1}/{len(stock_codes)}] {progress:.1f}% | 速度: {speed:.0f}只/秒 | 剩余: {eta:.0f}秒 | 已耗时: {elapsed:.1f}秒", flush=True)
                last_progress_time = current_time

            # 获取股票名称
            stock_name = stock_dict.get(stock_code, '')

            # 扫描TD序列
            result = self.scan_stock_td(stock_code, stock_name, periods)

            # 检查是否至少有一个周期达到最小TD计数
            max_td_count = 0
            for period in periods:
                if result.get(period):
                    max_td_count = max(max_td_count, result[period]['td_count'])

            # 只有至少有一个周期有数据才添加到结果
            if max_td_count > 0:
                all_results.append(result)

                # 检查是否满足条件
                if max_td_count >= min_td_count:
                    qualified_stocks.append(result)

        # 统计信息
        elapsed = time.time() - start_time
        print(f"\n✓ 扫描完成!")
        print(f"总扫描: {len(stock_codes)} 只股票")
        print(f"成功获取数据: {len(all_results)} 只")

        # 统计各周期符合条件的情况
        print(f"\n各周期TD序列统计:")
        for period in periods:
            period_name = period_names.get(period, period)
            count_9 = sum(1 for r in all_results if r.get(period) and r[period]['td_count'] >= 9)
            count_8 = sum(1 for r in all_results if r.get(period) and r[period]['td_count'] >= 8)
            count_7 = sum(1 for r in all_results if r.get(period) and r[period]['td_count'] >= 7)
            print(f"  {period_name}: 9底={count_9}只, 8底+={count_8}只, 7底+={count_7}只")

        print(f"\n符合条件(TD≥{min_td_count}): {len(qualified_stocks)} 只")
        print(f"耗时: {elapsed:.1f}秒\n")

        # 保存结果
        if save_results:
            self._save_results(qualified_stocks, all_results, periods, min_td_count)

        return qualified_stocks, all_results

    def _save_results(self, qualified_stocks, all_results, periods, min_td_count):
        """保存扫描结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        period_names = {
            'daily': '日K',
            'weekly': '周K',
            'monthly': '月K'
        }

        # 保存所有结果（详细版）
        if all_results:
            df_all = self._results_to_dataframe(all_results, periods)
            file_all = os.path.join(self.output_dir, f'td_all_results_{timestamp}.xlsx')
            df_all.to_excel(file_all, index=False, engine='openpyxl')
            print(f"✓ 所有结果已保存: {file_all}")

        # 保存符合条件的结果
        if qualified_stocks:
            df_qualified = self._results_to_dataframe(qualified_stocks, periods)
            file_qualified = os.path.join(self.output_dir, f'td_qualified_{min_td_count}plus_{timestamp}.xlsx')
            df_qualified.to_excel(file_qualified, index=False, engine='openpyxl')
            print(f"✓ 符合条件结果已保存: {file_qualified}\n")

        # 按周期分别保存
        for period in periods:
            period_name = period_names.get(period, period)
            period_results = [r for r in all_results if r.get(period)]

            if period_results:
                df_period = self._period_results_to_dataframe(period_results, period)
                file_period = os.path.join(self.output_dir, f'td_{period}_{timestamp}.xlsx')
                df_period.to_excel(file_period, index=False, engine='openpyxl')
                print(f"✓ {period_name}结果已保存: {file_period}")

        print()

    def _results_to_dataframe(self, results, periods):
        """将所有结果转换为DataFrame"""
        data = []

        for result in results:
            row = {
                '代码': result['code'],
                '名称': result['name']
            }

            # 添加各周期信息
            for period in periods:
                if result.get(period):
                    row[f'{period}_日期'] = result[period]['date']
                    row[f'{period}_收盘'] = result[period]['close']
                    row[f'{period}_TD计数'] = result[period]['td_count']
                    row[f'{period}_9底'] = '✓' if result[period]['td_9'] else ''
                    row[f'{period}_8底+'] = '✓' if result[period]['td_8'] else ''
                    row[f'{period}_7底+'] = '✓' if result[period]['td_7'] else ''
                else:
                    row[f'{period}_日期'] = ''
                    row[f'{period}_收盘'] = ''
                    row[f'{period}_TD计数'] = ''
                    row[f'{period}_9底'] = ''
                    row[f'{period}_8底+'] = ''
                    row[f'{period}_7底+'] = ''

            # 计算最大TD计数
            max_td = 0
            for period in periods:
                if result.get(period):
                    max_td = max(max_td, result[period]['td_count'])
            row['最大TD计数'] = max_td

            data.append(row)

        return pd.DataFrame(data)

    def _period_results_to_dataframe(self, results, period):
        """将单个周期的结果转换为DataFrame"""
        data = []

        for result in results:
            if not result.get(period):
                continue

            period_data = result[period]
            row = {
                '代码': result['code'],
                '名称': result['name'],
                '日期': period_data['date'],
                '收盘价': period_data['close'],
                'TD计数': period_data['td_count'],
                '9底': '✓' if period_data['td_9'] else '',
                '8底+': '✓' if period_data['td_8'] else '',
                '7底+': '✓' if period_data['td_7'] else ''
            }
            data.append(row)

        return pd.DataFrame(data)

    def generate_report(self, qualified_stocks, all_results, periods):
        """生成扫描报告"""
        period_names = {
            'daily': '日K',
            'weekly': '周K',
            'monthly': '月K'
        }

        print("\n" + "="*70)
        print("TD序列扫描报告")
        print("="*70)

        if qualified_stocks:
            print(f"\n【符合条件股票 ({len(qualified_stocks)}只)】")
            print("-"*70)

            for i, stock in enumerate(qualified_stocks, 1):
                print(f"\n{i}. {stock['code']} {stock['name']}")

                for period in periods:
                    if stock.get(period):
                        period_name = period_names.get(period, period)
                        td_count = stock[period]['td_count']
                        date = stock[period]['date']
                        close = stock[period]['close']

                        signal_text = []
                        if stock[period]['td_9']:
                            signal_text.append('9底')
                        elif stock[period]['td_8']:
                            signal_text.append('8底')
                        elif stock[period]['td_7']:
                            signal_text.append('7底')

                        if signal_text:
                            print(f"   {period_name}: TD={td_count} ({', '.join(signal_text)}) | {date} | 收盘:{close}")
                        elif td_count >= 4:
                            print(f"   {period_name}: TD={td_count} (进行中) | {date} | 收盘:{close}")

        print("\n" + "="*70 + "\n")


def scan_td_full_market(periods=['daily', 'weekly', 'monthly'], min_td_count=7):
    """
    扫描全市场TD序列

    Parameters:
    -----------
    periods : list
        要分析的周期列表
    min_td_count : int
        最小TD计数
    """
    period_names = {
        'daily': '日K',
        'weekly': '周K',
        'monthly': '月K'
    }
    period_str = '、'.join([period_names.get(p, p) for p in periods])

    print("\n" + "="*70)
    print(f"全市场TD序列扫描 - {period_str}")
    print("="*70 + "\n")

    scanner = TDScanner(
        data_dir='./data',
        output_dir='./output'
    )

    # 扫描全市场
    qualified, all_results = scanner.scan_stock_list(
        stock_list=None,
        periods=periods,
        min_td_count=min_td_count,
        save_results=True
    )

    # 生成报告
    scanner.generate_report(qualified, all_results, periods)

    return qualified, all_results


def scan_td_custom_stocks(stock_codes, periods=['daily', 'weekly', 'monthly'], min_td_count=7):
    """
    扫描自定义股票列表的TD序列

    Parameters:
    -----------
    stock_codes : list
        股票代码列表
    periods : list
        要分析的周期列表
    min_td_count : int
        最小TD计数
    """
    period_names = {
        'daily': '日K',
        'weekly': '周K',
        'monthly': '月K'
    }
    period_str = '，'.join([period_names.get(p, p) for p in periods])

    print("\n" + "="*70)
    print(f"自定义股票池TD序列扫描 - {period_str}")
    print("="*70 + "\n")

    scanner = TDScanner(
        data_dir='./data',
        output_dir='./output'
    )

    # 扫描自定义列表
    qualified, all_results = scanner.scan_stock_list(
        stock_list=stock_codes,
        periods=periods,
        min_td_count=min_td_count,
        save_results=True
    )

    # 生成报告
    scanner.generate_report(qualified, all_results, periods)

    return qualified, all_results


def scan_td_top_stocks(n=300, periods=['daily', 'weekly', 'monthly'], min_td_count=7):
    """
    扫描前N只股票（用于快速测试）

    Parameters:
    -----------
    n : int
        扫描股票数量
    periods : list
        要分析的周期列表
    min_td_count : int
        最小TD计数
    """
    period_names = {
        'daily': '日K',
        'weekly': '周K',
        'monthly': '月K'
    }
    period_str = '，'.join([period_names.get(p, p) for p in periods])

    print("\n" + "="*70)
    print(f"快速测试 - 扫描前{n}只股票 - {period_str}")
    print("="*70 + "\n")

    scanner = TDScanner(
        data_dir='./data',
        output_dir='./output'
    )

    # 获取全市场列表
    print("正在获取股票列表...")
    all_stocks_dict = scanner.data_fetcher.get_stock_list()

    # 取前N只
    stock_codes = list(all_stocks_dict.keys())[:n]
    test_stocks = {code: all_stocks_dict[code] for code in stock_codes}

    # 扫描
    qualified, all_results = scanner.scan_stock_list(
        stock_list=test_stocks,
        periods=periods,
        min_td_count=min_td_count,
        save_results=True
    )

    # 生成报告
    scanner.generate_report(qualified, all_results, periods)

    return qualified, all_results


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='TD序列扫描器')
    parser.add_argument('--mode', type=str, default='test',
                        choices=['full', 'test', 'custom'],
                        help='扫描模式: full=全市场, test=测试前N只, custom=自定义列表')
    parser.add_argument('--n', type=int, default=300,
                        help='测试模式下扫描的股票数量')
    parser.add_argument('--min-td', type=int, default=7,
                        help='最小TD计数 (7=7底及以上, 8=8底及以上, 9=仅9底)')
    parser.add_argument('--periods', type=str, nargs='+',
                        choices=['daily', 'weekly', 'monthly'],
                        default=['daily', 'weekly', 'monthly'],
                        help='要分析的周期 (默认全部)')
    parser.add_argument('--stocks', type=str, nargs='+',
                        help='自定义股票代码列表 (如: 000001 000002 600000)')

    args = parser.parse_args()

    if args.mode == 'full':
        # 全市场扫描
        scan_td_full_market(periods=args.periods, min_td_count=args.min_td)

    elif args.mode == 'test':
        # 测试模式 - 扫描前N只
        scan_td_top_stocks(n=args.n, periods=args.periods, min_td_count=args.min_td)

    elif args.mode == 'custom':
        # 自定义列表
        if not args.stocks:
            print("✗ 自定义模式需要提供股票代码列表")
            print("  使用示例: python run_td_scan.py --mode custom --stocks 000001 000002 600000")
        else:
            scan_td_custom_stocks(args.stocks, periods=args.periods, min_td_count=args.min_td)
