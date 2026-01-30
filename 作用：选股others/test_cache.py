# -*- coding: utf-8 -*-
"""
测试缓存功能
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from data_fetcher import DataFetcher
import time


def test_cache():
    """测试缓存"""
    print('\n测试缓存功能...\n')

    # 使用 jiudi 的缓存目录
    fetcher = DataFetcher(
        cache_dir='C:/Users/Administrator/Desktop/作用：选股jiudi/data',
        cache_days=1
    )

    # 测试加载已有缓存
    print('[1/2] 测试从缓存加载 000001...')
    start = time.time()
    df1 = fetcher.get_stock_data_for_analysis('000001', days_needed=60)
    elapsed1 = time.time() - start

    if df1 is not None:
        print(f'  成功! 数据量: {len(df1)} 条, 耗时: {elapsed1:.3f}秒')
        print(f'  最新日期: {df1["date"].iloc[-1].strftime("%Y-%m-%d")}')
        print(f'  收盘价: {df1["close"].iloc[-1]:.2f}\n')
    else:
        print('  失败\n')

    # 再次加载，应该直接从缓存读取
    print('[2/2] 测试再次从缓存加载 000001...')
    start = time.time()
    df2 = fetcher.get_stock_data_for_analysis('000001', days_needed=60)
    elapsed2 = time.time() - start

    if df2 is not None:
        print(f'  成功! 数据量: {len(df2)} 条, 耗时: {elapsed2:.3f}秒')
        print(f'  速度提升: {elapsed1/elapsed2:.1f}x\n')
    else:
        print('  失败\n')

    print('='*60)
    print('缓存测试完成!')
    print('='*60)


if __name__ == '__main__':
    test_cache()
