"""
测试新的分类逻辑（包含序列7-8）
"""
import sys
import io
from pathlib import Path

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))

from jiudi_scanner import JiuDiScanner
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

print("=" * 60)
print("测试新的分类逻辑（包含序列7-8）")
print("=" * 60)
print()

scanner = JiuDiScanner(output_dir='./output')

# 获取股票列表并过滤主板股票
print("正在获取股票列表...")
fetcher = scanner.fetcher
stock_list_full = fetcher.get_stock_list()

# 过滤主板股票（6开头沪市，0开头深市）
main_board = stock_list_full[
    (stock_list_full['code'].str.startswith('6')) |
    (stock_list_full['code'].str.startswith('0'))
].head(100)  # 测试100只

print(f"主板股票共 {len(main_board)} 只（已选择前100只）")
print()

# 手动扫描这100只股票
print("开始扫描...")
print()

results = []
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

print("\n" + "=" * 60)
print("测试完成！请查看output目录中的结果文件")
print("=" * 60)
