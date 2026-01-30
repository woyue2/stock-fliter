"""
组合信号扫描器
基于多技术指标（MACD、RSI、KDJ、成交量、均线等）的综合选股系统
与九底扫描器（jiudi_scanner.py）区分，专注于常规技术指标
"""
import sys
import io
# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
from pathlib import Path
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from multi_indicator_analyzer import analyze_all_signals, classify_signal_level
from data_fetcher import StockDataFetcher


class ComboSignalScanner:
    """组合信号扫描器"""

    def __init__(self, output_dir: str = './output_combo'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fetcher = StockDataFetcher()

        # 结果存储（按评分级别分类）
        self.strong_buy = []      # 🔥 强烈买入 (score >= 10)
        self.buy = []             # ⚡ 买入 (7-9分)
        self.watch_buy = []       # ⚠️ 观察买入 (5-6分)
        self.attention = []       # 👀 关注 (3-4分)
        self.all_results = []     # 所有结果

    def analyze_single_stock(self, code: str, name: str) -> dict:
        """
        分析单只股票

        参数:
            code: 股票代码
            name: 股票名称

        返回:
            分析结果字典
        """
        # 尝试从缓存加载
        cached_data = self.fetcher.load_from_cache(code, max_age_days=0)

        if cached_data:
            daily_df = cached_data.get('daily')
        else:
            # 获取日K数据
            daily_df, _, _ = self.fetcher.get_multi_period_data(code)

            # 保存到缓存
            if daily_df is not None:
                self.fetcher.save_to_cache(code, daily_df, None, None)

        # 数据检查
        if daily_df is None or len(daily_df) < 60:
            return None

        # 计算所有技术指标
        try:
            signals = analyze_all_signals(daily_df)
        except Exception as e:
            return None

        # 组装结果
        result = {
            'code': code,
            'name': name,
            'score': signals['score'],
            'signal_level': classify_signal_level(signals['score'], signals['signals']),
            'signals_count': len(signals['signals']),
            'signals': ', '.join(signals['signals']),
            'latest_price': signals['latest_price'],
            'latest_date': signals['latest_date'],
            # MACD
            'macd_dif': signals['macd']['dif'],
            'macd_dea': signals['macd']['dea'],
            'macd_golden_cross': signals['macd']['golden_cross'],
            'macd_above_zero': signals['macd']['above_zero'],
            # RSI
            'rsi': signals['rsi']['rsi'],
            'rsi_oversold': signals['rsi']['oversold'],
            # KDJ
            'kdj_k': signals['kdj']['k'],
            'kdj_d': signals['kdj']['d'],
            'kdj_golden_cross': signals['kdj']['golden_cross'],
            # 成交量
            'volume_ratio': signals['volume']['volume_ratio'],
            'volume_surge': signals['volume']['volume_surge'],
            'volume_up_price_up': signals['volume']['volume_up_price_up'],
            # 均线
            'ma_bullish': signals['ma_trend']['bullish_alignment'],
            'price_above_ma': signals['ma_trend']['price_above_all'],
            # 突破
            'breakout': signals['breakout']['breakout_recent'],
        }

        return result

    def scan_market(self, max_workers: int = 10, limit: int = None,
                    min_score: int = 3):
        """
        扫描全市场

        参数:
            max_workers: 线程数
            limit: 限制扫描数量（用于测试）
            min_score: 最低评分（低于此分数不保存）
        """
        print("=" * 60)
        print("🚀 组合信号选股系统")
        print("基于MACD、RSI、KDJ、成交量、均线等多指标分析")
        print("=" * 60)

        # 获取股票列表
        stock_list = self.fetcher.get_stock_list()

        if stock_list is None or len(stock_list) == 0:
            print("❌ 无法获取股票列表")
            return

        # 限制数量（测试用）
        if limit:
            stock_list = stock_list.head(limit)
            print(f"📊 测试模式：扫描前 {limit} 只股票\n")
        else:
            print(f"📊 全市场扫描：共 {len(stock_list)} 只股票\n")

        # 多线程扫描
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            future_to_stock = {}
            for _, stock in stock_list.iterrows():
                future = executor.submit(
                    self.analyze_single_stock,
                    stock['code'],
                    stock['name']
                )
                future_to_stock[future] = stock

            # 进度条
            with tqdm(total=len(future_to_stock), desc="扫描进度") as pbar:
                for future in as_completed(future_to_stock):
                    stock = future_to_stock[future]
                    try:
                        result = future.result(timeout=30)
                        if result and result['score'] >= min_score:
                            results.append(result)
                    except Exception as e:
                        pass  # 静默处理错误

                    pbar.update(1)

        # 分类结果
        self._classify_results(results)

        # 输出统计
        self._print_summary()

    def _classify_results(self, results: list):
        """分类分析结果"""
        for r in results:
            self.all_results.append(r)

            score = r['score']

            # 按评分分类
            if score >= 10:
                self.strong_buy.append(r)
            elif score >= 7:
                self.buy.append(r)
            elif score >= 5:
                self.watch_buy.append(r)
            elif score >= 3:
                self.attention.append(r)

    def _print_summary(self):
        """打印统计摘要"""
        total = len(self.all_results)

        print("\n" + "=" * 60)
        print("📊 扫描完成！统计结果：")
        print("=" * 60)
        print(f"✅ 有效信号：{total} 只（评分≥3）")
        print(f"\n🔥 完美形态：")
        print(f"   强烈买入（≥10分）：{len(self.strong_buy)} 只")
        print(f"\n⚡ 买入机会：")
        print(f"   买入信号（7-9分）：{len(self.buy)} 只")
        print(f"\n⚠️ 值得关注：")
        print(f"   观察买入（5-6分）：{len(self.watch_buy)} 只")
        print(f"   关注（3-4分）：{len(self.attention)} 只")
        print("=" * 60)

    def save_results(self):
        """保存分析结果"""
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 1. 保存强烈买入（最推荐）
        if self.strong_buy:
            df = pd.DataFrame(self.strong_buy)
            df = df.sort_values('score', ascending=False)

            # 选择关键列显示
            display_cols = ['code', 'name', 'score', 'signals', 'latest_price', 'macd_golden_cross',
                          'rsi_oversold', 'kdj_golden_cross', 'volume_surge', 'ma_bullish']

            file_path = self.output_dir / f'强烈买入_{date_str}.csv'
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f"\n💾 强烈买入结果：{file_path}")

            print("\n" + "🔥" * 30)
            print("强烈买入信号股票（重点推荐）：")
            print("🔥" * 30)
            print(df[display_cols].to_string(index=False))

        # 2. 保存买入信号
        if self.buy:
            df = pd.DataFrame(self.buy)
            df = df.sort_values('score', ascending=False)

            display_cols = ['code', 'name', 'score', 'signals', 'latest_price']

            file_path = self.output_dir / f'买入信号_{date_str}.csv'
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f"\n💾 买入信号结果：{file_path}")

            print("\n" + "⚡" * 30)
            print("买入信号股票（重点关注）：")
            print("⚡" * 30)
            print(df[display_cols].head(20).to_string(index=False))

        # 3. 保存观察买入
        if self.watch_buy:
            df = pd.DataFrame(self.watch_buy)
            df = df.sort_values('score', ascending=False)

            file_path = self.output_dir / f'观察买入_{date_str}.csv'
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f"\n💾 观察买入结果：{file_path}")

        # 4. 保存关注
        if self.attention:
            df = pd.DataFrame(self.attention)
            df = df.sort_values('score', ascending=False)

            file_path = self.output_dir / f'关注列表_{date_str}.csv'
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f"\n💾 关注列表结果：{file_path}")

        # 5. 保存所有结果
        if self.all_results:
            df_all = pd.DataFrame(self.all_results)
            df_all = df_all.sort_values('score', ascending=False)

            file_path = self.output_dir / f'全部信号_{date_str}.csv'
            df_all.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f"\n💾 全部结果：{file_path}")

    def scan_custom_pool(self, stock_codes: list, stock_names: dict = None):
        """
        扫描自定义股票池

        参数:
            stock_codes: 股票代码列表
            stock_names: 股票代码到名称的映射（可选）
        """
        print("=" * 60)
        print("🎯 自定义股票池扫描")
        print("=" * 60)
        print(f"📊 共 {len(stock_codes)} 只股票\n")

        results = []
        for code in stock_codes:
            name = stock_names.get(code, code) if stock_names else code
            result = self.analyze_single_stock(code, name)
            if result and result['score'] >= 3:
                results.append(result)

        # 分类结果
        self._classify_results(results)

        # 输出统计
        self._print_summary()


def main():
    """主函数"""
    scanner = ComboSignalScanner(output_dir='./output_combo')

    # 扫描全市场
    # 可以设置 limit=100 来测试前100只股票
    scanner.scan_market(
        max_workers=20,  # 线程数
        limit=None,      # None=全市场，或设置数字如100
        min_score=3      # 最低评分
    )

    # 保存结果
    scanner.save_results()


if __name__ == '__main__':
    main()
