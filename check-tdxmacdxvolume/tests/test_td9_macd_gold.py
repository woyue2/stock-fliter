#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试是否有股票同时符合TD9和MACD零轴下金叉条件
"""
import sys
from pathlib import Path

# 添加项目路径
project_dir = Path(__file__).resolve().parent
sys.path.append(str(project_dir))
sys.path.append(str(project_dir / "util"))

import pandas as pd
from data_loader import load_daily_data, iter_stock_items


def test_td9_macd_gold_combination():
    """测试是否有股票同时符合TD9和MACD零轴下金叉条件"""
    
    print("测试是否有股票同时符合TD9和MACD零轴下金叉条件...\n")
    
    # 添加util目录到路径
    util_dir = project_dir / ".." / "util"
    sys.path.append(str(util_dir.resolve()))
    
    from indicators_lib import TechnicalIndicators
    
    # 加载股票数据
    items = list(iter_stock_items(limit=100))
    
    count = 0
    found = []
    
    for item in items:
        count += 1
        print(f"分析第 {count}/{len(items)} 只股票: {item.code} - {item.name}")
        
        df = load_daily_data(item.code)
        
        if df.empty:
            continue
            
        if len(df) < 60:
            continue
            
        # 计算指标
        close = df["close"]
        
        # 检查TD9
        td_seq = TechnicalIndicators.calculate_td_sequence(close)
        td_count = td_seq.iloc[-1]
        is_td9 = td_count >= 9
        
        # 检查MACD零轴下金叉
        is_macd_gold = TechnicalIndicators.check_macd_golden_cross_below_zero(close)
        
        # 检查是否同时符合
        if is_td9 and is_macd_gold:
            print(f"✅ 找到同时符合条件的股票: {item.code} - {item.name} (TD计数: {td_count})")
            found.append((item.code, item.name, td_count))
    
    print(f"\n{'='*50}")
    print(f"分析完成！")
    print(f"总分析股票数: {count}")
    print(f"同时符合TD9和MACD零轴下金叉条件的股票数: {len(found)}")
    
    if found:
        print(f"\n符合条件的股票:")
        for code, name, td_count in found:
            print(f"  • {code} - {name} (TD计数: {td_count})")
    
    return found


if __name__ == "__main__":
    results = test_td9_macd_gold_combination()
