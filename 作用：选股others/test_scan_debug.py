# -*- coding: utf-8 -*-
"""
测试扫描并输出调试信息
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

print('\n快速测试 - 扫描前 10 只股票\n')

# 获取股票列表
print('[1/2] 获取股票列表...')
start = time.time()
stock_dict = scanner.data_fetcher.get_stock_list()
list_time = time.time() - start
print(f'  耗时: {list_time:.1f}秒\n')

# 取前10只
stock_codes = list(stock_dict.keys())[:10]
test_stocks = {code: stock_dict[code] for code in stock_codes}

# 扫描
print('[2/2] 扫描股票...')
start = time.time()
for i, code in enumerate(stock_codes):
    t0 = time.time()
    result = scanner.scan_single_stock(code, stock_dict[code])
    t1 = time.time()
    print(f'  {i+1}. {code} {stock_dict[code]}: {t1-t0:.3f}秒', end='')
    if result:
        print(f' [信号: {result["signals"]["signal_count"]}]')
    else:
        print()

scan_time = time.time() - start
print(f'\n总扫描时间: {scan_time:.1f}秒')
print(f'平均每只: {scan_time/len(stock_codes):.3f}秒')
