#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试MACD强度计算函数
"""
import sys
from pathlib import Path

# 添加项目路径
project_dir = Path(__file__).resolve().parent
sys.path.append(str(project_dir))
sys.path.append(str(project_dir / "check-new-indicators"))
sys.path.append(str(project_dir / "util"))

import pandas as pd
from data_loader import load_daily_data, iter_stock_items


def test_macd_strength():
    """测试MACD强度计算"""
    
    print("测试MACD强度计算...\n")
    
    # 加载股票数据
    items = list(iter_stock_items(limit=2))
    
    for item in items:
        print(f"股票: {item.code} - {item.name}")
        df = load_daily_data(item.code)
        
        if df.empty:
            print(f"无数据\n")
            continue
            
        if len(df) < 60:
            print(f"数据不足\n")
            continue
            
        print(f"数据长度: {len(df)}")
        
        # 计算MACD值
        from indicators_lib import TechnicalIndicators
        close = df["close"]
        
        # 计算MACD
        macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(close)
        
        print(f"MACD线值 (最新): {macd_line.iloc[-1]:.4f}")
        print(f"信号线值 (最新): {signal_line.iloc[-1]:.4f}")
        print(f"柱状图值 (最新): {histogram.iloc[-1]:.4f}")
        
        # 检查MACD金叉
        is_macd_gold = TechnicalIndicators.check_macd_golden_cross_below_zero(close)
        print(f"MACD零轴下金叉: {is_macd_gold}")
        
        # 计算MACD强度
        macd_strength = 0
        if is_macd_gold:
            macd_value = macd_line.iloc[-1]
            macd_strength = max(0, min(100, int((-macd_value / 2) * 100)))
            
        print(f"MACD强度: {macd_strength}")
        print()


if __name__ == "__main__":
    test_macd_strength()
