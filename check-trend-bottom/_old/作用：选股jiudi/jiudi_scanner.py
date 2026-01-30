"""
三周期九底共振选股主程序
扫描A股市场，找出日K、周K、月K同时达到九底的股票
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

from td_sequential import get_td_signal_info, analyze_resonance
from data_fetcher import StockDataFetcher


class JiuDiScanner:
    """九底共振扫描器"""

    def __init__(self, output_dir: str = './output'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fetcher = StockDataFetcher()

        # 结果存储
        self.resonance_stocks = []  # 三周期共振（≥9）
        self.near_resonance = []    # 接近共振（序列7-8）
        self.double_resonance = []  # 双周期共振（≥9）
        self.single_jiudi = []      # 单周期九底（≥9）
        self.near_jiudi = []        # 接近九底（序列7-8）
        self.all_results = []       # 所有分析结果

    def prepare_cache(self, limit: int = None, max_workers: int = 10):
        """
        预获取所有股票数据并保存到缓存（两步走第一步）

        参数:
            limit: 限制数量（用于测试）
            max_workers: 线程数
        """
        print("=" * 60)
        print("📦 第一步：预获取股票数据到缓存")
        print("=" * 60)

        # 获取股票列表
        stock_list = self.fetcher.get_stock_list()

        if stock_list is None or len(stock_list) == 0:
            print("❌ 无法获取股票列表")
            return

        # 限制数量
        if limit:
            stock_list = stock_list.head(limit)
            print(f"📊 测试模式：预获取前 {limit} 只股票\n")
        else:
            print(f"📊 全市场预获取：共 {len(stock_list)} 只股票\n")

        success_count = 0
        fail_count = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_stock = {}
            for _, stock in stock_list.iterrows():
                future = executor.submit(
                    self.fetcher.get_multi_period_data,
                    stock['code']
                )
                future_to_stock[future] = stock['code']

            with tqdm(total=len(future_to_stock), desc="预获取进度") as pbar:
                for future in as_completed(future_to_stock):
                    code = future_to_stock[future]
                    try:
                        daily_df, weekly_df, monthly_df = future.result(timeout=60)

                        if daily_df is not None and len(daily_df) >= 50:
                            self.fetcher.save_to_cache(code, daily_df, weekly_df, monthly_df)
                            success_count += 1
                        else:
                            fail_count += 1
                    except Exception as e:
                        fail_count += 1

                    pbar.update(1)

        print(f"\n✅ 预获取完成：成功 {success_count} 只，失败 {fail_count} 只")
        print("📁 数据已保存到 data/ 目录")

    def analyze_single_stock(self, code: str, name: str, use_cache: bool = True) -> dict:
        """
        分析单只股票

        参数:
            code: 股票代码
            name: 股票名称
            use_cache: 是否优先从缓存读取（第二步使用）

        返回:
            分析结果字典
        """
        daily_df = None
        weekly_df = None
        monthly_df = None

        # 尝试从缓存加载
        if use_cache:
            cached_data = self.fetcher.load_from_cache(code, max_age_days=7)  # 7天内缓存有效

            if cached_data:
                daily_df = cached_data.get('daily')
                weekly_df = cached_data.get('weekly')
                monthly_df = cached_data.get('monthly')

        # 如果没有缓存或不使用缓存，则实时获取
        if daily_df is None:
            daily_df, weekly_df, monthly_df = self.fetcher.get_multi_period_data(code)

            # 保存到缓存
            if daily_df is not None:
                self.fetcher.save_to_cache(code, daily_df, weekly_df, monthly_df)

        # 数据检查
        if daily_df is None or len(daily_df) < 50:
            return None

        if weekly_df is None or len(weekly_df) < 30:
            return None

        if monthly_df is None or len(monthly_df) < 12:
            return None

        # 计算TD序列
        daily_signal = get_td_signal_info(daily_df)
        weekly_signal = get_td_signal_info(weekly_df)
        monthly_signal = get_td_signal_info(monthly_df)

        # 分析共振
        resonance = analyze_resonance(daily_signal, weekly_signal, monthly_signal)

        # 组装结果
        result = {
            'code': code,
            'name': name,
            'latest_price': daily_signal['latest_close'],
            'latest_date': daily_signal['latest_date'],
            'daily_count': daily_signal['current_buy'],
            'weekly_count': weekly_signal['current_buy'],
            'monthly_count': monthly_signal['current_buy'],
            'is_resonance': resonance['is_resonance'],
            'resonance_level': resonance['resonance_level'],
            'jiudi_cycles': resonance['jiudi_cycles'],
        }

        return result

    def scan_market(self, max_workers: int = 10, limit: int = None, use_cache_only: bool = False):
        """
        扫描全市场（两步走第二步：只读取缓存进行分析）

        参数:
            max_workers: 线程数
            limit: 限制扫描数量（用于测试）
            use_cache_only: 是否只使用缓存（True=两步走模式，False=传统模式）
        """
        print("=" * 60)
        print("🚀 三周期九底共振选股系统")
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
                    stock['name'],
                    use_cache=(not use_cache_only)  # 传统模式=实时获取+缓存；两步走=只读缓存
                )
                future_to_stock[future] = stock

            # 进度条
            with tqdm(total=len(future_to_stock), desc="分析进度") as pbar:
                for future in as_completed(future_to_stock):
                    stock = future_to_stock[future]
                    try:
                        result = future.result(timeout=30)  # 30秒超时
                        if result:
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

            # 统计各周期的序列值
            daily = r['daily_count']
            weekly = r['weekly_count']
            monthly = r['monthly_count']

            # 判断各周期是否达到九底（≥9）
            daily_jiudi = daily >= 9
            weekly_jiudi = weekly >= 9
            monthly_jiudi = monthly >= 9

            # 判断各周期是否接近九底（7-8）
            daily_near = 7 <= daily < 9
            weekly_near = 7 <= weekly < 9
            monthly_near = 7 <= monthly < 9

            # 1. 三周期共振（三个周期都≥9）
            if daily_jiudi and weekly_jiudi and monthly_jiudi:
                self.resonance_stocks.append(r)

            # 2. 接近三周期共振（三个周期都≥7）
            elif (daily >= 7 and weekly >= 7 and monthly >= 7):
                self.near_resonance.append(r)

            # 3. 双周期共振（两个周期≥9）
            elif sum([daily_jiudi, weekly_jiudi, monthly_jiudi]) == 2:
                self.double_resonance.append(r)

            # 4. 单周期九底（一个周期≥9）
            elif sum([daily_jiudi, weekly_jiudi, monthly_jiudi]) == 1:
                self.single_jiudi.append(r)

            # 5. 接近九底（至少一个周期7-8）
            elif sum([daily_near, weekly_near, monthly_near]) >= 1:
                self.near_jiudi.append(r)

    def _print_summary(self):
        """打印统计摘要"""
        total = len(self.all_results)

        print("\n" + "=" * 60)
        print("📊 扫描完成！统计结果：")
        print("=" * 60)
        print(f"✅ 有效分析：{total} 只")
        print(f"\n🔥 完美形态：")
        print(f"   三周期共振（≥9）：{len(self.resonance_stocks)} 只")
        print(f"   接近三周期共振（≥7）：{len(self.near_resonance)} 只")
        print(f"\n⚡ 常见形态：")
        print(f"   双周期共振（≥9）：{len(self.double_resonance)} 只")
        print(f"   单周期九底（≥9）：{len(self.single_jiudi)} 只")
        print(f"\n⚠️  值得关注：")
        print(f"   接近九底（序列7-8）：{len(self.near_jiudi)} 只")
        print("=" * 60)

    def save_results(self):
        """保存分析结果"""
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 1. 保存三周期共振（最推荐）
        if self.resonance_stocks:
            df_resonance = pd.DataFrame(self.resonance_stocks)
            df_resonance = df_resonance.sort_values('monthly_count', ascending=False)

            file_resonance = self.output_dir / f'三周期九底共振_{date_str}.csv'
            df_resonance.to_csv(file_resonance, index=False, encoding='utf-8-sig')
            print(f"\n💾 三周期共振结果：{file_resonance}")

            # 打印共振股票
            print("\n" + "🔥" * 30)
            print("三周期九底共振股票（重点推荐）：")
            print("🔥" * 30)
            print(df_resonance[['code', 'name', 'latest_price', 'daily_count', 'weekly_count', 'monthly_count']].to_string(index=False))

        # 2. 保存接近三周期共振
        if self.near_resonance:
            df_near = pd.DataFrame(self.near_resonance)
            df_near = df_near.sort_values('monthly_count', ascending=False)

            file_near = self.output_dir / f'接近三周期共振_{date_str}.csv'
            df_near.to_csv(file_near, index=False, encoding='utf-8-sig')
            print(f"\n💾 接近三周期共振结果：{file_near}")

            print("\n" + "⚡" * 30)
            print("接近三周期共振股票（重点关注）：")
            print("⚡" * 30)
            print(df_near[['code', 'name', 'latest_price', 'daily_count', 'weekly_count', 'monthly_count']].to_string(index=False))

        # 3. 保存双周期共振
        if self.double_resonance:
            df_double = pd.DataFrame(self.double_resonance)
            df_double = df_double.sort_values('monthly_count', ascending=False)

            file_double = self.output_dir / f'双周期共振_{date_str}.csv'
            df_double.to_csv(file_double, index=False, encoding='utf-8-sig')
            print(f"\n💾 双周期共振结果：{file_double}")

        # 4. 保存单周期九底
        if self.single_jiudi:
            df_single = pd.DataFrame(self.single_jiudi)
            df_single = df_single.sort_values(['daily_count', 'weekly_count', 'monthly_count'], ascending=False)

            file_single = self.output_dir / f'单周期九底_{date_str}.csv'
            df_single.to_csv(file_single, index=False, encoding='utf-8-sig')
            print(f"\n💾 单周期九底结果：{file_single}")

        # 5. 保存接近九底（序列7-8）
        if self.near_jiudi:
            df_near_jiudi = pd.DataFrame(self.near_jiudi)
            # 按最大序列值排序
            df_near_jiudi['max_seq'] = df_near_jiudi[['daily_count', 'weekly_count', 'monthly_count']].max(axis=1)
            df_near_jiudi = df_near_jiudi.sort_values('max_seq', ascending=False)
            df_near_jiudi = df_near_jiudi.drop('max_seq', axis=1)

            file_near_jiudi = self.output_dir / f'接近九底_{date_str}.csv'
            df_near_jiudi.to_csv(file_near_jiudi, index=False, encoding='utf-8-sig')
            print(f"\n💾 接近九底结果：{file_near_jiudi}")

            print("\n" + "⚠️" * 30)
            print("接近九底股票（序列7-8，值得留意）：")
            print("⚠️" * 30)
            print(df_near_jiudi[['code', 'name', 'latest_price', 'daily_count', 'weekly_count', 'monthly_count']].to_string(index=False))

        # 6. 保存所有结果
        if self.all_results:
            df_all = pd.DataFrame(self.all_results)
            # 按最大序列值排序
            df_all['max_seq'] = df_all[['daily_count', 'weekly_count', 'monthly_count']].max(axis=1)
            df_all = df_all.sort_values('max_seq', ascending=False)
            df_all = df_all.drop('max_seq', axis=1)

            file_all = self.output_dir / f'全部分析结果_{date_str}.csv'
            df_all.to_csv(file_all, index=False, encoding='utf-8-sig')
            print(f"\n💾 全部结果：{file_all}")

    def two_step_scan(self, max_workers: int = 10, limit: int = None):
        """
        两步走扫描模式：
        1. 预获取所有股票数据到缓存
        2. 从缓存读取数据进行TD序列分析

        参数:
            max_workers: 线程数
            limit: 限制数量（用于测试）
        """
        # 第一步：预获取数据
        self.prepare_cache(limit=limit, max_workers=max_workers)

        print()

        # 第二步：分析结果
        self.scan_market(max_workers=max_workers, limit=limit, use_cache_only=True)

        # 保存结果
        self.save_results()


def main():
    """主函数"""
    scanner = JiuDiScanner(output_dir='./output')

    # 使用两步走模式（推荐）：
    # 1. 先批量下载数据到 data/ 目录
    # 2. 然后快速分析（适合多次分析场景）
    scanner.two_step_scan(
        max_workers=20,  # 线程数，根据网络情况调整
        limit=None        # None=全市场，或设置数字如100
    )


if __name__ == '__main__':
    main()
