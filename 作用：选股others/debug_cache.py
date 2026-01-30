# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from data_fetcher import DataFetcher
from pathlib import Path

# 测试缓存命中
cache_dir = Path('C:/Users/Administrator/Desktop/作用：选股jiudi/data')
fetcher = DataFetcher(cache_dir=str(cache_dir), cache_days=1)

print('检查缓存目录...')
print(f'缓存目录: {cache_dir}')
print(f'缓存文件数量: {len(list(cache_dir.glob("*.pkl")))}')

# 测试几个股票代码
test_codes = ['000001', '000002', '600000', '600519', '000725']
print(f'\n测试缓存命中:')
for code in test_codes:
    cache_file = cache_dir / f'{code}.pkl'
    exists = cache_file.exists()
    print(f'  {code}.pkl 存在: {exists}')

# 尝试加载数据
print(f'\n测试数据加载:')
import time
for code in test_codes[:3]:
    start = time.time()
    df = fetcher.get_stock_data_for_analysis(code, days_needed=60)
    elapsed = time.time() - start
    if df is not None:
        print(f'  {code}: 成功 ({len(df)}条) {elapsed:.3f}秒')
    else:
        print(f'  {code}: 失败 {elapsed:.3f}秒')
