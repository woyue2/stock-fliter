# -*- coding: utf-8 -*-
"""
测试时间分配
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from data_fetcher import DataFetcher
from technical_indicators import TechnicalIndicators
import time

fetcher = DataFetcher(
    cache_dir='C:/Users/Administrator/Desktop/作用：选股jiudi/data',
    cache_days=1
)
indicators = TechnicalIndicators()

print('测试时间分配...\n')

test_code = '000001'

# 测试数据加载时间
print('[1/2] 测试数据加载...')
start = time.time()
df = fetcher.get_stock_data_for_analysis(test_code, days_needed=60)
load_time = time.time() - start
print(f'  耗时: {load_time:.3f}秒')

# 测试指标计算时间
print('\n[2/2] 测试指标计算...')
close_prices = df['close']
volumes = df['volume']

start = time.time()
signals = indicators.check_all_signals(close_prices, volumes)
calc_time = time.time() - start
print(f'  耗时: {calc_time:.3f}秒')
print(f'  信号数: {signals["signal_count"]}')

print(f'\n总耗时: {load_time + calc_time:.3f}秒')
print(f'数据加载占比: {load_time/(load_time+calc_time)*100:.1f}%')
print(f'指标计算占比: {calc_time/(load_time+calc_time)*100:.1f}%')
