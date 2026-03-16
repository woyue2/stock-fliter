import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional

from util.db import get_daily_data, get_stock_info_map
from .analyzers.magic_number_analyzer import MagicNumberAnalyzer
from .analyzers.smile_analyzer import SmileAnalyzer

class SmileMagicPipeline:
    """
    Coordinator for the Smile Number Strategy.
    Fetches data, runs analyzers, and filters results.
    """
    
    def __init__(self):
        self.stock_info = get_stock_info_map()
        
    def run(self, code_list: Optional[List[str]] = None, target_date: Optional[str] = None) -> pd.DataFrame:
        """
        Run the analysis for a list of stocks.
        """
        if code_list is None:
            code_list = list(self.stock_info.keys())
            
        results = []
        
        for code in code_list:
            # Fetch at least 200 days to ensure smile/peak/rolling calculations are valid
            df = get_daily_data(code, days=250)
            if df.empty or len(df) < 120:
                continue
                
            # Filter for target_date if provided
            if target_date:
                # Ensure the date exists or take the last available up to target_date
                df_filtered = df[df['date'] <= pd.to_datetime(target_date)]
                if df_filtered.empty:
                    continue
                df_to_analyze = df_filtered
            else:
                df_to_analyze = df
                
            # 1. Smile Analysis
            smile_res = SmileAnalyzer.analyze(df_to_analyze)
            if smile_res.empty:
                continue
                
            # 2. Magic Number Analysis
            magic_res = MagicNumberAnalyzer.analyze(df_to_analyze)
            
            # 3. Additional Base Conditions
            # 新低 := L = LLV(L, 10);
            low_10 = df_to_analyze['low'].rolling(window=10).min()
            is_new_low = df_to_analyze['low'] == low_10
            
            # Relaxed Yang Line: Close >= Open * 0.998 (Allows small doji/stars)
            is_valid_candle = df_to_analyze['close'] >= df_to_analyze['open'] * 0.998
            
            # Combine all for the last row
            last_idx = df_to_analyze.index[-1]
            
            final_select = is_valid_candle.loc[last_idx] and \
                           is_new_low.loc[last_idx] and \
                           magic_res.loc[last_idx] and \
                           smile_res['is_smile'].loc[last_idx]
            
            if final_select:
                name = self.stock_info.get(code, {}).get('name', 'N/A')
                results.append({
                    'code': code,
                    'name': name,
                    'date': df_to_analyze['date'].iloc[-1].strftime('%Y-%m-%d'),
                    'price': df_to_analyze['close'].iloc[-1],
                    'low': df_to_analyze['low'].iloc[-1],
                    'peak': smile_res['peak_h'].iloc[-1],
                    'box_low': smile_res['box_low'].iloc[-1]
                })
                
        return pd.DataFrame(results)
