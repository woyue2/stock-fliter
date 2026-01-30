# -*- coding: utf-8 -*-
"""
指数成分股TD序列扫描器
专门分析沪深300、中证500、中证1000、上证50的成分股TD序列（日K、周K、月K）
"""
import sys
import io
import os
import time
import pandas as pd
import akshare as ak
from datetime import datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from data_fetcher import DataFetcher
from technical_indicators import TechnicalIndicators


class IndexTDScanner:
    """指数成分股TD序列扫描器"""

    # 定义指数配置
    INDEX_CONFIG = {
        '沪深300': {
            'name': '沪深300',
            'index_code': '000300',
            'stock_count': 300,
            'description': '大盘蓝筹'
        },
        '中证500': {
            'name': '中证500',
            'index_code': '000905',
            'stock_count': 500,
            'description': '中盘股'
        },
        '中证1000': {
            'name': '中证1000',
            'index_code': '000852',
            'stock_count': 1000,
            'description': '小盘股'
        },
        '上证50': {
            'name': '上证50',
            'index_code': '000016',
            'stock_count': 50,
            'description': '超级蓝筹'
        }
    }

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

    def get_index_stocks(self, index_name):
        """
        获取指数成分股

        Parameters:
        -----------
        index_name : str
            指数名称：'沪深300', '中证500', '中证1000', '上证50'

        Returns:
        --------
        dict
            {股票代码: 股票名称}
        """
        if index_name not in self.INDEX_CONFIG:
            print(f"✗ 不支持的指数: {index_name}")
            return {}

        config = self.INDEX_CONFIG[index_name]
        print(f"\n正在获取{config['name']}成分股...")

        try:
            # 使用akshare获取指数成分股
            if index_name == '沪深300':
                df = ak.index_stock_cons(symbol="000300")
            elif index_name == '中证500':
                df = ak.index_stock_cons(symbol="000905")
            elif index_name == '中证1000':
                df = ak.index_stock_cons(symbol="000852")
            elif index_name == '上证50':
                df = ak.index_stock_cons(symbol="000016")
            else:
                return {}

            if df is not None and len(df) > 0:
                # 提取股票代码和名称
                stock_dict = dict(zip(df['品种代码'], df['品种名称']))

                # 保存成分股列表
                csv_file = os.path.join(self.data_dir, f"{index_name}_成分股_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                df.to_csv(csv_file, index=False, encoding='utf-8-sig')

                print(f"✓ 获取{config['name']}成分股 {len(stock_dict)} 只")
                return stock_dict
            else:
                print(f"✗ 获取{config['name']}成分股失败")
                return {}

        except Exception as e:
            print(f"✗ 获取{config['name']}成分股失败: {e}")
            return {}

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
            df = self.data_fetcher.get_stock_data(
                stock_code,
                period=period,
                start_date='20200101',
                save_to_file=False  # 不保存文件，避免过多文件
            )

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

    def scan_index(self, index_name, periods=['daily', 'weekly', 'monthly'],
                   min_td_count=7, save_results=True):
        """
        扫描单个指数的成分股

        Parameters:
        -----------
        index_name : str
            指数名称
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
        # 获取指数成分股
        stock_dict = self.get_index_stocks(index_name)

        if not stock_dict:
            print(f"✗ {index_name} 成分股为空")
            return [], []

        stock_codes = list(stock_dict.keys())
        config = self.INDEX_CONFIG[index_name]

        period_names = {
            'daily': '日K',
            'weekly': '周K',
            'monthly': '月K'
        }
        period_str = '、'.join([period_names.get(p, p) for p in periods])

        print(f"\n{'='*70}")
        print(f"{config['name']}（{config['description']}）TD序列扫描")
        print(f"成分股数量: {len(stock_codes)} 只")
        print(f"分析周期: {period_str}")
        print(f"筛选条件: TD计数 ≥ {min_td_count}")
        print(f"{'='*70}\n")

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
                print(f"[{i + 1}/{len(stock_codes)}] {progress:.1f}% | 速度: {speed:.0f}只/秒 | 剩余: {eta:.0f}秒", flush=True)
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
        print(f"\n✓ {config['name']}扫描完成!")
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
            self._save_results(qualified_stocks, all_results, periods, min_td_count, index_name)

        return qualified_stocks, all_results

    def _save_results(self, qualified_stocks, all_results, periods, min_td_count, index_name):
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
            file_all = os.path.join(self.output_dir, f'{index_name}_所有结果_{timestamp}.xlsx')
            df_all.to_excel(file_all, index=False, engine='openpyxl')
            print(f"✓ {index_name}所有结果已保存: {file_all}")

        # 保存符合条件的结果
        if qualified_stocks:
            df_qualified = self._results_to_dataframe(qualified_stocks, periods)
            file_qualified = os.path.join(self.output_dir, f'{index_name}_{min_td_count}底以上_{timestamp}.xlsx')
            df_qualified.to_excel(file_qualified, index=False, engine='openpyxl')
            print(f"✓ {index_name}符合条件结果已保存: {file_qualified}\n")

        # 按周期分别保存
        for period in periods:
            period_name = period_names.get(period, period)
            period_results = [r for r in all_results if r.get(period)]

            if period_results:
                df_period = self._period_results_to_dataframe(period_results, period)
                file_period = os.path.join(self.output_dir, f'{index_name}_{period_name}_{timestamp}.xlsx')
                df_period.to_excel(file_period, index=False, engine='openpyxl')
                print(f"✓ {index_name}{period_name}结果已保存: {file_period}")

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

    def generate_report(self, qualified_stocks, all_results, periods, index_name):
        """生成扫描报告"""
        config = self.INDEX_CONFIG[index_name]
        period_names = {
            'daily': '日K',
            'weekly': '周K',
            'monthly': '月K'
        }

        print("\n" + "="*70)
        print(f"{config['name']}（{config['description']}）TD序列扫描报告")
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


def scan_single_index(index_name, periods=['daily', 'weekly', 'monthly'], min_td_count=7):
    """
    扫描单个指数

    Parameters:
    -----------
    index_name : str
        指数名称：'沪深300', '中证500', '中证1000', '上证50'
    periods : list
        要分析的周期列表
    min_td_count : int
        最小TD计数
    """
    scanner = IndexTDScanner(
        data_dir='./data',
        output_dir='./output'
    )

    # 扫描指数
    qualified, all_results = scanner.scan_index(
        index_name=index_name,
        periods=periods,
        min_td_count=min_td_count,
        save_results=True
    )

    # 生成报告
    scanner.generate_report(qualified, all_results, periods, index_name)

    return qualified, all_results


def scan_all_indices(periods=['daily', 'weekly', 'monthly'], min_td_count=7):
    """
    扫描所有指数

    Parameters:
    -----------
    periods : list
        要分析的周期列表
    min_td_count : int
        最小TD计数
    """
    index_names = ['沪深300', '中证500', '中证1000', '上证50']

    print("\n" + "="*70)
    print(f"全指数成分股TD序列扫描")
    print(f"扫描指数: {', '.join(index_names)}")
    print("="*70 + "\n")

    all_results_by_index = {}

    for index_name in index_names:
        qualified, all_results = scan_single_index(index_name, periods, min_td_count)
        all_results_by_index[index_name] = {
            'qualified': qualified,
            'all': all_results
        }

    # 生成汇总报告
    print("\n" + "="*70)
    print("全指数扫描汇总报告")
    print("="*70)

    for index_name, results in all_results_by_index.items():
        config = IndexTDScanner.INDEX_CONFIG[index_name]
        print(f"\n{config['name']}（{config['description']}）:")
        print(f"  符合条件: {len(results['qualified'])} 只")
        print(f"  成功扫描: {len(results['all'])} 只")

    print("\n" + "="*70 + "\n")

    return all_results_by_index


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='指数成分股TD序列扫描器')
    parser.add_argument('--index', type=str, default='all',
                        choices=['all', '沪深300', '中证500', '中证1000', '上证50'],
                        help='要扫描的指数 (默认扫描所有)')
    parser.add_argument('--min-td', type=int, default=7,
                        help='最小TD计数 (7=7底及以上, 8=8底及以上, 9=仅9底)')
    parser.add_argument('--periods', type=str, nargs='+',
                        choices=['daily', 'weekly', 'monthly'],
                        default=['daily', 'weekly', 'monthly'],
                        help='要分析的周期 (默认全部)')

    args = parser.parse_args()

    if args.index == 'all':
        # 扫描所有指数
        scan_all_indices(periods=args.periods, min_td_count=args.min_td)
    else:
        # 扫描单个指数
        scan_single_index(args.index, periods=args.periods, min_td_count=args.min_td)
