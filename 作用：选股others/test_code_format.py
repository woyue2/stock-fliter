# -*- coding: utf-8 -*-
"""
测试股票代码格式
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from data_fetcher import DataFetcher
from pathlib import Path

fetcher = DataFetcher(
    cache_dir='C:/Users/Administrator/Desktop/作用：选股jiudi/data',
    cache_days=1
)

print('获取股票列表...\n')
stock_dict = fetcher.get_stock_list()
stock_codes = list(stock_dict.keys())[:10]

print('股票列表格式:')
for code in stock_codes[:5]:
    name = stock_dict[code]
    print(f'  {code!r} -> {name} (长度: {len(code)})')

print('\n检查缓存文件...')
cache_dir = Path('C:/Users/Administrator/Desktop/作用：选股jiudi/data')
cache_files = sorted([f.stem for f in cache_dir.glob('*.pkl')])[:10]
print('缓存文件名:')
for name in cache_files:
    print(f'  {name!r}')

print('\n对比:')
test_code = stock_codes[0]
print(f'股票代码: {test_code!r}')
print(f'是否匹配缓存: {test_code in cache_files}')
