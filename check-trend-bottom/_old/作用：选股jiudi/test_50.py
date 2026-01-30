"""
小规模扫描测试（前50只主板股票）
"""
import sys
import os
import time
from pathlib import Path

# 设置UTF-8编码输出
os.environ['PYTHONIOENCODING'] = 'utf-8'

sys.path.insert(0, str(Path(__file__).parent))

from jiudi_scanner import JiuDiScanner
import pandas as pd


def get_stock_list_with_retry(fetcher, max_retries=3, delay=5):
    """带重试机制的股票列表获取函数"""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"正在获取股票列表 (第 {attempt}/{max_retries} 次尝试)...")
            stock_list = fetcher.get_stock_list()

            # 检查返回结果是否有效
            if stock_list is None or len(stock_list) == 0:
                if attempt < max_retries:
                    print(f"  → 获取结果为空，等待 {delay} 秒后重试...")
                    time.sleep(delay)
                else:
                    print("[X] 重试次数耗尽，无法获取股票列表")
                    return None
                continue

            print(f"成功获取 {len(stock_list)} 只股票")
            return stock_list

        except Exception as e:
            print(f"[X] 获取股票列表失败: {e}")
            if attempt < max_retries:
                print(f"  → 等待 {delay} 秒后重试...")
                time.sleep(delay)
            else:
                print("[X] 重试次数耗尽，无法获取股票列表")
                return None


print("=" * 60)
print("小规模扫描测试（前50只主板股票）")
print("=" * 60)
print()

scanner = JiuDiScanner(output_dir='./output')

# 获取股票列表并过滤主板股票
fetcher = scanner.fetcher
stock_list_full = get_stock_list_with_retry(fetcher)

if stock_list_full is None or len(stock_list_full) == 0:
    print("\n错误: 无法获取股票列表数据，请检查网络连接后重试")
    print("提示: akshare 可能有临时网络问题，稍后重试即可")
    sys.exit(1)

# 过滤主板股票（6开头沪市，0开头深市）
main_board = stock_list_full[
    (stock_list_full['code'].str.startswith('6')) |
    (stock_list_full['code'].str.startswith('0'))
].head(50)

print(f"\n主板股票共 {len(main_board)} 只（已选择前50只）")
print()

# 手动扫描这50只股票
print("开始扫描...")
print()

results = []
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

with ThreadPoolExecutor(max_workers=5) as executor:
    future_to_stock = {}
    for _, stock in main_board.iterrows():
        future = executor.submit(
            scanner.analyze_single_stock,
            stock['code'],
            stock['name']
        )
        future_to_stock[future] = stock

    with tqdm(total=len(future_to_stock), desc="扫描进度") as pbar:
        for future in as_completed(future_to_stock):
            try:
                result = future.result(timeout=30)
                if result:
                    results.append(result)
            except Exception as e:
                pass
            pbar.update(1)

# 分类结果
scanner._classify_results(results)

# 打印统计
scanner._print_summary()

# 保存结果
scanner.save_results()
