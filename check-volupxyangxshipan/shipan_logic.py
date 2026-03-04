# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  df(pd.DataFrame) 单股日线数据
# OUTPUT: Tuple[int, str] 试盘次数和详细描述
# POS:    check-volupxyangxshipan/shipan_logic.py
# -*- coding: utf-8 -*-
import pandas as pd
from typing import Tuple, Optional

def analyze_shipan_behavior(df: pd.DataFrame) -> Tuple[int, str]:
    """
    分析主力试盘行为 (纯 Pandas 向量化实现)
    返回: (试盘次数, 详细描述)
    """
    if df is None or len(df) < 30:
        return 0, ""

    full_df = df.copy()
    high_250 = full_df['high'].rolling(window=min(len(full_df), 250)).max().iloc[-1]
    full_df['v_ma20'] = full_df['volume'].rolling(window=20).mean()
    full_df['prev_close'] = full_df['close'].shift(1)
    
    scan_df = full_df.tail(45).copy()
    
    pct_chg = (scan_df['close'] - scan_df['prev_close']) / scan_df['prev_close'] * 100
    
    day_range = (scan_df['high'] - scan_df['low']).clip(lower=0.01)
    body = (scan_df['close'] - scan_df['open']).abs()
    
    # 向量化求 max(open, close) 和 min(open, close)
    max_oc = scan_df[['open', 'close']].max(axis=1)
    min_oc = scan_df[['open', 'close']].min(axis=1)
    
    upper_shadow = scan_df['high'] - max_oc
    lower_shadow = min_oc - scan_df['low']
    
    vol = scan_df['volume']
    v_ma20 = scan_df['v_ma20']
    
    cond_valid = (v_ma20 > 0) & (scan_df['close'] < high_250 * 0.8)
    
    cond_limit = (pct_chg > 7.0) & (vol > v_ma20 * 1.3)
    cond_upper = (upper_shadow > body * 1.5) & (upper_shadow > day_range * 0.4) & (vol > v_ma20 * 1.5)
    cond_lower = (lower_shadow > body * 1.5) & (vol > v_ma20 * 1.1)
    
    scan_df['shipan_type'] = None
    # 优先级: 下影 < 上影 < 涨停 (后赋值覆盖前赋值)
    scan_df.loc[cond_valid & cond_lower, 'shipan_type'] = "下影"
    scan_df.loc[cond_valid & cond_upper, 'shipan_type'] = "上影"
    scan_df.loc[cond_valid & cond_limit, 'shipan_type'] = "涨停"
    
    hits = scan_df[scan_df['shipan_type'].notna()].copy()
    if hits.empty:
        return 0, ""
        
    dates = pd.to_datetime(hits['date']).dt.strftime("%m-%d")
    details = dates + "(" + hits['shipan_type'] + ")"
    
    return len(details), ",".join(details.tolist())
