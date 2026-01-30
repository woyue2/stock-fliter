# -*- coding: utf-8 -*-
"""
测试TD序列功能
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from stock_scanner import StockScanner

print('\n[测试] TD序列功能\n')

scanner = StockScanner(
    output_dir='./output',
    cache_dir='C:/Users/Administrator/Desktop/作用：选股jiudi/data'
)

# 获取股票列表
stock_dict = scanner.data_fetcher.get_stock_list()

# 测试几个股票
test_codes = ['000001', '600519', '000002']

print(f'测试TD序列计算:\n')

for code in test_codes:
    result = scanner.scan_single_stock(code, stock_dict.get(code, ''))
    if result:
        td_count = result['signals']['td_count']
        td_9 = result['signals']['td_9']
        td_8 = result['signals']['td_8']
        td_7 = result['signals']['td_7']

        print(f"{code} {stock_dict[code]}:")
        print(f"  TD序列计数: {td_count}")
        print(f"  9底: {'✓' if td_9 else '✗'}")
        print(f"  8底+: {'✓' if td_8 else '✗'}")
        print(f"  7底+: {'✓' if td_7 else '✗'}")
    else:
        print(f"{code} 无信号")
    print()

print('\n扫描TD 7底+的股票...\n')

# 获取前100只股票
stock_codes = list(stock_dict.keys())[:100]
test_stocks = {code: stock_dict[code] for code in stock_codes}

qualified, all_results = scanner.scan_stock_list(
    stock_list=test_stocks,
    min_signals=1,  # 至少1个信号
    save_results=False
)

# 筛选TD 7底+
td_stocks = [r for r in all_results if r['signals'].get('td_7', False)]

print(f'\n找到 {len(td_stocks)} 只TD 7底+的股票')

if td_stocks:
    print('\n【TD 7底+ 股票列表】')
    for i, stock in enumerate(td_stocks, 1):
        td_count = stock['signals']['td_count']
        print(f"{i}. {stock['code']} {stock['name']} - TD {td_count}底")
