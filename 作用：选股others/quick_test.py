# -*- coding: utf-8 -*-
"""
快速测试扫描速度
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from stock_scanner import StockScanner
import time

scanner = StockScanner(
    output_dir='./output',
    cache_dir='C:/Users/Administrator/Desktop/作用：选股jiudi/data'
)

print('\n测试扫描速度...\n')

# 获取股票列表
stock_dict = scanner.data_fetcher.get_stock_list(use_cache=True)
stock_codes = list(stock_dict.keys())

# 测试扫描500只
test_count = 500
print(f'扫描前 {test_count} 只股票...')

start = time.time()
qualified, all_results = scanner.scan_stock_list(
    stock_list={code: stock_dict[code] for code in stock_codes[:test_count]},
    min_signals=2,
    save_results=False
)
elapsed = time.time() - start

print(f'\n实际扫描耗时: {elapsed:.2f}秒')
print(f'平均每只: {elapsed/test_count:.4f}秒')
print(f'预估全市场(5472只): {elapsed/test_count*5472:.1f}秒')

if qualified:
    print(f'\n找到 {len(qualified)} 只符合条件的股票（2个以上信号）')
    for stock in qualified[:5]:
        signals = [k for k, v in stock['signals'].items() if v and k != 'signal_count']
        print(f"  {stock['code']} {stock['name']}: {', '.join(signals)}")
