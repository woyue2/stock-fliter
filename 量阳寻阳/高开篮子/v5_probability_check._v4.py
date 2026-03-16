#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v5 策略胜率统计脚本 V4
用途：统计 '量阳寻阳/v5条件.csv' 定义的策略。

策略执行逻辑 [V4 - 波段持仓版]:
1. 买入点：设定为 T-1 日（信号触发日）的开盘价 (Open)。
2. 卖出点（强制持有 + 重心追踪）：
   - 强制持有期：无论价格波动，至少持有 2 个交易日（T 日和 T+1 日）。
   - 重心判定标准：K 线中点价格 MiddlePoint (MP) = (Open + Close) / 2。
   - 规则：从第 2 个交易日 (T+1) 起检查重心。
     * 如果重心稳定上升 (MP[today] > MP[yesterday])，则继续持股。
     * 如果重心不再上升 (MP[today] <= MP[yesterday])，则立即在当天收盘卖出。
     * 最终卖出点：如果前 2 天重心就没稳住，第 2 天收盘即卖出；否则在重心转弱当天收盘卖出。
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
    检查索引 i 处的 T-1 日是否满足 v5 策略的买入基础形态。
    """
    if i < 45 or i + 1 >= len(df):
        return False

    d1 = df.iloc[i]   # T-1
    d2 = df.iloc[i-1] # T-2
    d3 = df.iloc[i-2] # T-3
    d4 = df.iloc[i-3] # T-4
    d5 = df.iloc[i-4] # T-5
    d6 = df.iloc[i-5] # T-6

    # 1. T-3 爆量条件 (V3 > V4/V5/V6)
    if d3['volume'] <= d4['volume'] or d3['volume'] <= d5['volume'] or d3['volume'] <= d6['volume']:
        return False

    # 2. T-2 确认条件
    if not (d2['volume'] < d3['volume'] and d2['close'] > d2['open']):
        return False
    top3 = max(d3['open'], d3['close'])
    if not (d2['close'] > top3):
        return False
    mp2 = (d2['open'] + d2['close']) / 2
    mp3 = (d3['open'] + d3['close']) / 2
    mp4 = (d4['open'] + d4['close']) / 2
    if not (mp2 > mp3 > mp4):
        return False

    # 3. T-1 买入触发 (高开 O1 >= C2)
    if not (d1['open'] >= d2['close']):
        return False

    # 4. 试盘信号 (过去 45 天)
    sub_df = df.iloc[max(0, i-45):i].copy()
    shipan_count, _ = analyze_shipan_behavior(sub_df)
    if shipan_count < 1:
        return False

    return True

def main():
    print("正在加载股票信息 [V4: 强制2日+重心追踪模式]...")
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
            
        i = 45
        while i < len(df) - 2: # 至少预留2天数据
            if is_v5_match(df, i):
                buy_day = df.iloc[i]
                buy_price = buy_day['open']
                
                exit_price = None
                sell_type = ""
                hold_days = 0
                
                # 模拟持仓过程
                for j in range(i + 1, len(df)):
                    curr_day = df.iloc[j]
                    prev_day = df.iloc[j-1]
                    hold_days += 1
                    
                    # 规则：持仓至少达到 2 天 (即 j >= i+2) 后，检查重心
                    if hold_days >= 2:
                        curr_mp = (curr_day['open'] + curr_day['close']) / 2
                        prev_mp = (prev_day['open'] + prev_day['close']) / 2
                        
                        # 如果重心不再上升，当天收盘卖出
                        if curr_mp <= prev_mp:
                            exit_price = curr_day['close']
                            sell_type = f"重心转弱(第{hold_days}天卖出)"
                            break
                    
                    # 抵达数据末尾，强制结算
                    if j == len(df) - 1:
                        exit_price = curr_day['close']
                        sell_type = "持有至行情末尾"
                        break
                
                if exit_price is not None:
                    pct_chg = (exit_price - buy_price) / buy_price * 100
                    all_signals.append({
                        'code': code,
                        'name': name,
                        'buy_date': buy_day['date'],
                        'buy_price': buy_price,
                        'sell_price': exit_price,
                        'pct_chg': pct_chg,
                        'is_win': pct_chg > 0,
                        'hold_days': hold_days,
                        'sell_type': sell_type
                    })
                    # 跳过持仓期
                    i = j + 1
                    continue
            i += 1

    if not all_signals:
        print("未找到符合条件的信号。")
        return

    res_df = pd.DataFrame(all_signals)
    
    # 统计
    total = len(res_df)
    wins = res_df['is_win'].sum()
    win_rate = wins / total * 100
    avg_gain = res_df['pct_chg'].mean()
    avg_hold = res_df['hold_days'].mean()

    print("\n" + "="*40)
    print(f"策略名称: v5 策略 V4 (重心稳定追踪型)")
    print(f"统计样本: 共找到 {total} 个匹配信号")
    print(f"上涨概率: {win_rate:.2f}%")
    print(f"平均涨幅: {avg_gain:.2f}%")
    print(f"平均持仓: {avg_hold:.1f} 天")
    print("="*40)

    # 年份分析
    res_df['year'] = pd.to_datetime(res_df['buy_date']).dt.year
    yearly_stats = res_df.groupby('year').apply(lambda x: pd.Series({
        '信号数': len(x),
        '胜率': f"{(x['is_win'].sum()/len(x)*100):.2f}%",
        '均涨幅': f"{x['pct_chg'].mean():.2f}%",
        '均持仓': f"{x['hold_days'].mean():.1f}天"
    }))
    print("\n按年份拆分：")
    print(yearly_stats)

    # 保存
    output_dir = PROJECT_ROOT / "output" / "v5_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "v5_signals_detail_v4.csv"
    res_df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"\n明细已保存至: {out_path}")

if __name__ == "__main__":
    main()
