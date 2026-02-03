# -*- coding: utf-8 -*-
"""
第一步：获取所有股票数据并保存到缓存
"""
import sys
import time
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))

from data_fetcher import StockDataFetcher
from jiudi_scanner import JiuDiScanner  # noqa: F401
from log_util import setup_run_log


setup_run_log(Path(__file__))

print("=" * 60)
print("📌 第一步：获取股票数据到缓存")
print("=" * 60)
print()

fetcher = StockDataFetcher()

# 获取股票列表
print("正在获取股票列表...")
stock_list = fetcher.get_stock_list()

if stock_list is None or len(stock_list) == 0:
    print("❌ 无法获取股票列表")
    sys.exit(1)

print(f"✅ 获取到 {len(stock_list)} 只股票")
print()

# 预获取数据
success_count = 0
fail_count = 0
total = len(stock_list)

print("开始下载数据到缓存（预计 10-20 分钟）...")
print()

max_workers = 3
submit_delay = 0.05

with ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_to_stock = {}
    for _, stock in stock_list.iterrows():
        code = stock["code"]
        future = executor.submit(
            fetcher.get_multi_period_data,
            code,
        )
        future_to_stock[future] = code
        time.sleep(submit_delay)

    with tqdm(total=total, desc="下载进度") as pbar:
        for future in as_completed(future_to_stock):
            code = future_to_stock[future]
            try:
                daily_df, weekly_df, monthly_df = future.result(timeout=60)

                if daily_df is not None and len(daily_df) >= 50:
                    fetcher.save_to_cache(code, daily_df, weekly_df, monthly_df)
                    success_count += 1
                else:
                    fail_count += 1
            except Exception:
                fail_count += 1

            pbar.update(1)

print()
print("=" * 60)
print("✅ 数据获取完成")
print("=" * 60)
print(f"   成功：{success_count} 只")
print(f"   失败：{fail_count} 只")
print(f"   总计：{total} 只")
print()
print("📁 缓存位置：data/ 目录")
print("📌 下一步：运行 python test_300.py 进行分析")
print("=" * 60)
