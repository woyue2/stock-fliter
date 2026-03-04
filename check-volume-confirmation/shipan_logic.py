# -*- coding: utf-8 -*-
import pandas as pd
from typing import Tuple, Optional

def analyze_shipan_behavior(df: pd.DataFrame) -> Tuple[int, str]:
    """
    分析主力试盘行为
    返回: (试盘次数, 详细描述)
    """
    if df is None or len(df) < 30:
        return 0, ""

    shipan_count = 0
    details = []
    
    # 获取数据进行扫描 (考虑所有数据以计算准确的 MA)
    full_df = df.copy()
    
    # 辅助计算：250日最高价用于判断是否处于低位
    high_250 = full_df['high'].rolling(window=min(len(full_df), 250)).max().iloc[-1]
    
    # 计算20日均量
    full_df['v_ma20'] = full_df['volume'].rolling(window=20).mean()
    
    # 只扫描最近45天的数据 (约2个月)
    scan_df = full_df.tail(45)
    
    for i in range(len(scan_df)):
        idx = scan_df.index[i]
        row = scan_df.iloc[i]
        
        # 基础数据
        close = row['close']
        open_p = row['open']
        high = row['high']
        low = row['low']
        vol = row['volume']
        v_ma20 = row['v_ma20']
        
        if pd.isna(v_ma20) or v_ma20 == 0: continue
        
        # 振幅和实体
        day_range = high - low if high > low else 0.01
        body = abs(close - open_p)
        upper_shadow = high - max(open_p, close)
        lower_shadow = min(open_p, close) - low
        
        is_this_day_test = False
        test_type = ""
        
        # 获取昨日收盘价计算涨幅
        prev_idx = idx - 1
        if prev_idx in full_df.index:
            prev_close = full_df.loc[prev_idx, 'close']
            pct_chg = (close - prev_close) / prev_close * 100
        else:
            pct_chg = 0
        
        # 1. 涨停/准涨停试盘 (涨幅 > 7%, 且放量)
        if pct_chg > 7.0 and vol > v_ma20 * 1.3:
            is_this_day_test = True
            test_type = "涨停"
            
        # 2. 长上影线试盘 (上影线 > 实体 * 1.5 且 上影线 > 全天振幅 * 0.4, 且放量)
        elif upper_shadow > body * 1.5 and upper_shadow > day_range * 0.4 and vol > v_ma20 * 1.5:
            is_this_day_test = True
            test_type = "上影"
            
        # 3. 长下影线试盘 (下影线 > 实体 * 1.5, 且有一定成交量)
        elif lower_shadow > body * 1.5 and vol > v_ma20 * 1.1:
            is_this_day_test = True
            test_type = "下影"
            
        if is_this_day_test:
            # 过滤条件：位置不能太高 (当前价 < 250日高点的 80%)
            if close < high_250 * 0.8:
                shipan_count += 1
                date_str = pd.Timestamp(row['date']).strftime("%m-%d")
                details.append(f"{date_str}({test_type})")
                
    return shipan_count, ",".join(details)
