# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  df(pd.DataFrame) 单股日线数据
# OUTPUT: Tuple[int, str] 试盘次数和详细描述
# POS:    check-volume-confirmation/shipan_logic.py
# -*- coding: utf-8 -*-
import pandas as pd
from typing import Tuple, Optional

def _check_single_day_shipan(row: pd.Series, prev_close: float) -> Optional[str]:
    close = row['close']
    open_p = row['open']
    high = row['high']
    low = row['low']
    vol = row['volume']
    v_ma20 = row['v_ma20']
    
    if pd.isna(v_ma20) or v_ma20 == 0:
        return None
        
    day_range = high - low if high > low else 0.01
    body = abs(close - open_p)
    upper_shadow = high - max(open_p, close)
    lower_shadow = min(open_p, close) - low
    
    pct_chg = (close - prev_close) / prev_close * 100 if prev_close else 0
    
    if pct_chg > 7.0 and vol > v_ma20 * 1.3:
        return "涨停"
    if upper_shadow > body * 1.5 and upper_shadow > day_range * 0.4 and vol > v_ma20 * 1.5:
        return "上影"
    if lower_shadow > body * 1.5 and vol > v_ma20 * 1.1:
        return "下影"
    return None

def _process_scan_row(idx: int, row: pd.Series, full_df: pd.DataFrame, high_250: float) -> Optional[str]:
    prev_idx = idx - 1
    prev_close = full_df.loc[prev_idx, 'close'] if prev_idx in full_df.index else 0
    
    test_type = _check_single_day_shipan(row, prev_close)
    if test_type and row['close'] < high_250 * 0.8:
        date_str = pd.Timestamp(row['date']).strftime("%m-%d")
        return f"{date_str}({test_type})"
    return None

def analyze_shipan_behavior(df: pd.DataFrame) -> Tuple[int, str]:
    """
    分析主力试盘行为
    返回: (试盘次数, 详细描述)
    """
    if df is None or len(df) < 30:
        return 0, ""

    full_df = df.copy()
    high_250 = full_df['high'].rolling(window=min(len(full_df), 250)).max().iloc[-1]
    full_df['v_ma20'] = full_df['volume'].rolling(window=20).mean()
    
    scan_df = full_df.tail(45)
    details = []
    
    for i in range(len(scan_df)):
        idx = scan_df.index[i]
        row = scan_df.iloc[i]
        detail = _process_scan_row(idx, row, full_df, high_250)
        if detail:
            details.append(detail)
            
    return len(details), ",".join(details)
