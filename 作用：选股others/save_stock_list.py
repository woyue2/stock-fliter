# -*- coding: utf-8 -*-
"""
保存股票列表到本地缓存
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import akshare as ak
from pathlib import Path
from datetime import datetime

def save_stock_list():
    """保存股票列表"""
    cache_dir = Path('./cache')
    cache_dir.mkdir(exist_ok=True)

    print('获取A股股票列表...')
    stock_info = ak.stock_info_a_code_name()

    # 保存
    cache_file = cache_dir / 'stock_list.pkl'
    stock_info.to_pickle(cache_file)

    print(f'✓ 已保存 {len(stock_info)} 只股票到 {cache_file}')

    # 同时保存CSV方便查看
    csv_file = cache_dir / 'stock_list.csv'
    stock_info.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f'✓ 已保存CSV到 {csv_file}')

if __name__ == '__main__':
    save_stock_list()
