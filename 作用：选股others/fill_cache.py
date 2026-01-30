# -*- coding: utf-8 -*-
"""
为缺少缓存的股票补充缓存
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from data_fetcher import DataFetcher
from pathlib import Path
import time

cache_dir = Path('C:/Users/Administrator/Desktop/作用：选股jiudi/data')
fetcher = DataFetcher(cache_dir=str(cache_dir), cache_days=1)

print('检查缺少缓存的股票...\n')

stock_dict = fetcher.get_stock_list()
stock_codes = list(stock_dict.keys())

# 找出缺少缓存的股票
missing = []
for code in stock_codes:
    cache_file = cache_dir / f'{code}.pkl'
    if not cache_file.exists():
        missing.append(code)

print(f'发现 {len(missing)} 只股票缺少缓存\n')

# 下载缺失的缓存
if missing:
    print('开始下载缺失的缓存...\n')
    success_count = 0
    fail_count = 0

    for i, code in enumerate(missing, 1):
        print(f'[{i}/{len(missing)}] {code} {stock_dict[code]}...', end=' ', flush=True)

        start = time.time()
        df = fetcher.get_stock_data_for_analysis(code, days_needed=60)
        elapsed = time.time() - start

        if df is not None:
            success_count += 1
            print(f'✓ ({elapsed:.1f}秒)')
        else:
            fail_count += 1
            print(f'✗')

        # 避免请求过快
        time.sleep(0.2)

    print(f'\n✓ 缓存补充完成!')
    print(f'  成功: {success_count}')
    print(f'  失败: {fail_count}')
else:
    print('✓ 所有股票都有缓存')
