"""
测试沪深300股票 - 两步走模式（先缓存，再分析）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from jiudi_scanner import JiuDiScanner
import pandas as pd

print("=" * 60)
print("测试沪深300股票 - 两步走模式")
print("=" * 60)
print()

scanner = JiuDiScanner(output_dir='./output')

# 获取股票列表并过滤主板股票
print("正在获取股票列表...")
fetcher = scanner.fetcher
stock_list_full = fetcher.get_stock_list()

# 过滤主板股票（6开头沪市，0开头深市），取前300只
main_board = stock_list_full[
    (stock_list_full['code'].str.startswith('6')) |
    (stock_list_full['code'].str.startswith('0'))
].head(300)

print(f"主板股票共 {len(main_board)} 只（已选择前300只）")
print()

# 两步走模式
print("=" * 60)
print("📦 第一步：预获取数据到缓存")
print("=" * 60)
scanner.prepare_cache(limit=300, max_workers=10)

print()
print("=" * 60)
print("📊 第二步：从缓存分析数据")
print("=" * 60)

# 从缓存分析
scanner.scan_market(max_workers=10, limit=300, use_cache_only=True)

# 保存结果
scanner.save_results()

# 额外分析
print("\n" + "=" * 60)
print("📈 分析完成！结果已保存")
print("=" * 60)
