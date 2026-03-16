#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v5 策略胜率统计脚本 V2
用途：统计 '量阳寻阳/v5条件.csv' 定义的策略在历史上的胜率。

策略执行逻辑 [V2]:
1. 买入点：设定为 T-1 日（信号触发日）的开盘价 (Open)。
   逻辑：算法检测 T-3/T-2 形态完成。如果 T-1 日高开触发信号，假设在开盘瞬时即介入。
2. 卖出点：设定为 T 日（买入后的下一个交易日）的收盘价 (Close)。
   逻辑：无条件在买入后的次日收盘卖出（实际持股时间跨度为 T-1 开盘到 T 收盘）。
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from tqdm import tqdm

# 配置项目根目录到 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# 导入公共模块
from util.db import get_daily_data, get_stock_info_map
# 将 check-volupxyangxshipan--有用 添加到路径以导入 shipan_logic
STRATEGY_DIR = PROJECT_ROOT / "check-volupxyangxshipan--有用"
sys.path.append(str(STRATEGY_DIR))
from shipan_logic import analyze_shipan_behavior

def is_v5_match(df: pd.DataFrame, i: int) -> bool:
    """
    检查索引 i 处的 T-1 日是否满足 v5 策略的买入条件。
    i 是 T-1 日的索引。
    """
    if i < 45 or i + 1 >= len(df):
        return False

    # 定义各个日期
    # T   日: i + 1
    # T-1 日 (买入日): i
    # T-2 日 (确认日): i - 1
    # T-3 日 (爆量日): i - 2
    # T-4 日: i - 3
    # T-5 日: i - 4
    # T-6 日: i - 5

    d0 = df.iloc[i+1] # T
    d1 = df.iloc[i]   # T-1
    d2 = df.iloc[i-1] # T-2
    d3 = df.iloc[i-2] # T-3
    d4 = df.iloc[i-3] # T-4
    d5 = df.iloc[i-4] # T-5
    d6 = df.iloc[i-5] # T-6

    # 1. T-3 爆量条件 (V3 > V4/V5/V6)
    if not (d3['volume'] > d4['volume'] and d3['volume'] > d5['volume'] and d3['volume'] > d6['volume']):
        return False

    # 2. T-2 确认条件
    # 缩量 (V2 < V3) 且 收阳 (C2 > O2)
    if not (d2['volume'] < d3['volume'] and d2['close'] > d2['open']):
        return False
    # 突破爆量日实体上沿 (Top2 > Top3)
    top2 = d2['close'] # 阳线实体顶就是收盘价
    top3 = max(d3['open'], d3['close'])
    if not (top2 > top3):
        return False
    # 重心高于爆量日 (MP2 > MP3)
    mp2 = (d2['open'] + d2['close']) / 2
    mp3 = (d3['open'] + d3['close']) / 2
    if not (mp2 > mp3):
        return False
    # 特殊：重心还要高于 T-4 (MP2 > MP3 > MP4)
    mp4 = (d4['open'] + d4['close']) / 2
    if not (mp2 > mp3 > mp4):
        return False

    # 3. T-1 买入条件 (高开 O1 >= C2)
    if not (d1['open'] >= d2['close']):
        return False

    # 4. 试盘信号 (过去 45 天)
    sub_df = df.iloc[max(0, i-45):i].copy()
    shipan_count, _ = analyze_shipan_behavior(sub_df)
    if shipan_count < 1:
        return False

    return True

def main():
    print("正在加载股票信息 [V2: 开盘买入模式]...")
    stock_info = get_stock_info_map()
    
    valid_stocks = []
    for code, info in stock_info.items():
        if code.startswith(('30', '68')):
            continue
        if 'ST' in info['name'] or '*ST' in info['name']:
            continue
        valid_stocks.append((code, info['name']))
    
    print(f"有效标的共 {len(valid_stocks)} 只。")

    all_signals = []
    
    for code, name in tqdm(valid_stocks, desc="扫描股票进度"):
        df = get_daily_data(code, days=1000) 
        if df is None or len(df) < 50:
            continue
            
        for i in range(45, len(df) - 1):
            if is_v5_match(df, i):
                d0 = df.iloc[i+1] # T
                d1 = df.iloc[i]   # T-1
                # V2 逻辑：用 T 日收盘价对比 T-1 日开盘价
                buy_price = d1['open']
                sell_price = d0['close']
                pct_chg = (sell_price - buy_price) / buy_price * 100
                
                all_signals.append({
                    'code': code,
                    'name': name,
                    'date_match': d1['date'], # 买入信号触发日
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'pct_chg': pct_chg,
                    'is_win': pct_chg > 0
                })

    if not all_signals:
        print("未找到符合条件的信号。")
        return

    res_df = pd.DataFrame(all_signals)
    
    # 统计结果
    total = len(res_df)
    wins = res_df['is_win'].sum()
    win_rate = wins / total * 100
    avg_gain = res_df['pct_chg'].mean()

    print("\n" + "="*40)
    print(f"策略名称: v5 策略 V2 (开盘买入模式)")
    print(f"统计样本: 共找到 {total} 个匹配信号")
    print(f"上涨概率: {win_rate:.2f}%")
    print(f"平均涨幅: {avg_gain:.2f}%")
    print("="*40)

    # 按年份统计
    res_df['year'] = pd.to_datetime(res_df['date_match']).dt.year
    yearly_stats = res_df.groupby('year').apply(lambda x: pd.Series({
        '信号数': len(x),
        '胜率': f"{(x['is_win'].sum()/len(x)*100):.2f}%",
        '均涨幅': f"{x['pct_chg'].mean():.2f}%"
    }))
    print("\n按年份拆分：")
    print(yearly_stats)

    # 保存明细
    output_dir = PROJECT_ROOT / "output" / "v5_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "v5_signals_detail_v2.csv"
    res_df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"\n明细已保存至: {out_path}")

if __name__ == "__main__":
    main()
