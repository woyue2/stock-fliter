# -*- coding: utf-8 -*-
"""
选股扫描器
使用技术指标扫描符合条件的股票
"""
import os
import time
import pandas as pd
from datetime import datetime
from technical_indicators import TechnicalIndicators
from data_fetcher import DataFetcher


class StockScanner:
    """选股扫描器"""

    def __init__(self, output_dir='./output', data_dir='./data'):
        """
        初始化扫描器

        Parameters:
        -----------
        output_dir : str
            输出目录
        data_dir : str
            数据目录
        """
        self.output_dir = output_dir
        self.data_fetcher = DataFetcher(data_dir=data_dir)
        self.indicators = TechnicalIndicators()

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

    def scan_single_stock(self, stock_code, stock_name=''):
        """
        扫描单只股票

        Parameters:
        -----------
        stock_code : str
            股票代码
        stock_name : str
            股票名称

        Returns:
        --------
        dict or None
            扫描结果
        """
        # 获取数据
        df = self.data_fetcher.get_stock_data_for_analysis(stock_code, days_needed=60)

        if df is None or len(df) < 30:
            return None

        # 提取收盘价和成交量
        close_prices = df['close']
        volumes = df['volume']

        # 检测所有信号
        signals = self.indicators.check_all_signals(close_prices, volumes)

        # 始终返回结果（包括0个信号的）
        result = {
            'code': stock_code,
            'name': stock_name,
            'date': df['date'].iloc[-1].strftime('%Y-%m-%d'),
            'close': round(df['close'].iloc[-1], 2),
            'change_pct': round(df.get('change_pct', pd.Series([0])).iloc[-1], 2),
            'volume': int(df['volume'].iloc[-1]),
            'signals': signals
        }

        return result

    def scan_stock_list(self, stock_list=None, min_signals=1, save_results=True):
        """
        扫描股票列表

        Parameters:
        -----------
        stock_list : list or dict
            股票代码列表 或 {代码: 名称}字典，如果为None则获取全市场
        min_signals : int
            最少信号数量（过滤条件）
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

        print(f"\n开始扫描 {len(stock_codes)} 只股票...")
        print(f"筛选条件: 最少 {min_signals} 个信号\n")

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

            # 扫描单只股票
            result = self.scan_single_stock(stock_code, stock_name)

            if result:
                all_results.append(result)

                # 检查是否满足最少信号数
                if result['signals']['signal_count'] >= min_signals:
                    qualified_stocks.append(result)

        # 统计信息
        elapsed = time.time() - start_time
        print(f"\n✓ 扫描完成!")
        print(f"总扫描: {len(stock_codes)} 只股票")
        print(f"成功获取数据: {len(all_results)} 只")

        # 统计有信号的股票
        with_signal_count = sum(1 for r in all_results if r['signals']['signal_count'] > 0)
        print(f"有信号: {with_signal_count} 只")
        print(f"符合条件(≥{min_signals}个信号): {len(qualified_stocks)} 只")
        print(f"耗时: {elapsed:.1f}秒\n")

        # 保存结果
        if save_results:
            self._save_results(qualified_stocks, all_results, min_signals)

        return qualified_stocks, all_results

    def _save_results(self, qualified_stocks, all_results, min_signals):
        """保存扫描结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 保存符合条件的结果
        if qualified_stocks:
            df_qualified = self._results_to_dataframe(qualified_stocks)
            file_qualified = os.path.join(self.output_dir, f'qualified_{min_signals}signals_{timestamp}.xlsx')
            df_qualified.to_excel(file_qualified, index=False, engine='openpyxl')
            print(f"✓ 符合条件结果已保存: {file_qualified}")

        # 保存所有结果
        if all_results:
            df_all = self._results_to_dataframe(all_results)
            file_all = os.path.join(self.output_dir, f'all_results_{timestamp}.xlsx')
            df_all.to_excel(file_all, index=False, engine='openpyxl')
            print(f"✓ 所有结果已保存: {file_all}\n")

    def _results_to_dataframe(self, results):
        """将结果转换为DataFrame"""
        data = []

        for result in results:
            td_count = result['signals'].get('td_count', 0)

            row = {
                '代码': result['code'],
                '名称': result['name'],
                '日期': result['date'],
                '收盘价': result['close'],
                '涨跌幅(%)': result['change_pct'],
                '成交量': result['volume'],
                '信号数': result['signals']['signal_count'],
                '均线金叉': '✓' if result['signals']['ma_golden_cross'] else '',
                'MACD金叉': '✓' if result['signals']['macd_golden_cross'] else '',
                'MACD零轴下金叉': '✓' if result['signals']['macd_golden_cross_below_zero'] else '',
                'RSI超卖拐头': '✓' if result['signals']['rsi_oversold_turnup'] else '',
                '放量突破': '✓' if result['signals']['volume_breakout'] else '',
                'TD序列': td_count,
                '9底': '✓' if result['signals'].get('td_9', False) else '',
                '8底': '✓' if result['signals'].get('td_8', False) else '',
                '7底': '✓' if result['signals'].get('td_7', False) else ''
            }
            data.append(row)

        return pd.DataFrame(data)

    def generate_report(self, qualified_stocks, all_results):
        """生成扫描报告"""
        print("\n" + "="*60)
        print("扫描结果报告")
        print("="*60)

        # 信号统计
        signal_stats = {
            '均线金叉': sum(r['signals']['ma_golden_cross'] for r in all_results),
            'MACD金叉': sum(r['signals']['macd_golden_cross'] for r in all_results),
            'MACD零轴下金叉': sum(r['signals']['macd_golden_cross_below_zero'] for r in all_results),
            'RSI超卖拐头': sum(r['signals']['rsi_oversold_turnup'] for r in all_results),
            '放量突破': sum(r['signals']['volume_breakout'] for r in all_results),
            'TD 9底': sum(r['signals'].get('td_9', False) for r in all_results),
            'TD 8底+': sum(r['signals'].get('td_8', False) for r in all_results),
            'TD 7底+': sum(r['signals'].get('td_7', False) for r in all_results)
        }

        print("\n【信号统计】")
        for signal, count in signal_stats.items():
            print(f"  {signal}: {count} 次")

        # 符合条件的股票
        if qualified_stocks:
            print(f"\n【符合条件的股票 ({len(qualified_stocks)}只)】")
            print("-"*60)

            for i, stock in enumerate(qualified_stocks, 1):
                signals_text = []
                if stock['signals']['ma_golden_cross']:
                    signals_text.append('均线金叉')
                if stock['signals']['macd_golden_cross_below_zero']:
                    signals_text.append('MACD零轴下金叉')
                elif stock['signals']['macd_golden_cross']:
                    signals_text.append('MACD金叉')
                if stock['signals']['rsi_oversold_turnup']:
                    signals_text.append('RSI超卖拐头')
                if stock['signals']['volume_breakout']:
                    signals_text.append('放量突破')

                # 添加TD序列信息
                td_count = stock['signals'].get('td_count', 0)
                if td_count >= 7:
                    signals_text.append(f'TD {td_count}底')

                print(f"{i}. {stock['code']} {stock['name']} - {stock['date']}")
                print(f"   收盘: {stock['close']}  涨跌: {stock['change_pct']}%  信号: {', '.join(signals_text)}")

        print("\n" + "="*60 + "\n")


def main():
    """测试函数"""
    print("\n[测试] 股票扫描器\n")

    scanner = StockScanner(output_dir='./output')

    # 扫描全市场（最少2个信号）
    qualified, all_results = scanner.scan_stock_list(min_signals=2)

    # 生成报告
    scanner.generate_report(qualified, all_results)


if __name__ == '__main__':
    main()
