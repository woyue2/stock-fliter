import pandas as pd
import numpy as np

class SmileAnalyzer:
    """
    Smile Curve Analyzer (微笑曲线分析器)
    Implements cup-with-handle/box patterns based on specialized rules.
    """
    
    @staticmethod
    def analyze(df: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze OHLCV data for 'Smile Curve' patterns.
        Returns a DataFrame with intermediate flags and the final 'is_smile' flag.
        """
        if df.empty or len(df) < 60:
            return pd.DataFrame(index=df.index)
            
        res = pd.DataFrame(index=df.index)
        
        # --- 1. HHV (60-day high) and Peak detection ---
        # PEAK_H := HHV(H, 60); PEAK_DAY := HHVBARS(H, 60);
        res['peak_h'] = df['high'].rolling(window=60, min_periods=1).max()
        # Find index of rolling max to calculate "days since peak"
        def get_peak_day(x):
            if len(x) == 0: return 0
            return len(x) - 1 - np.argmax(x.values)
            
        res['peak_day'] = df['high'].rolling(window=60, min_periods=1).apply(get_peak_day, raw=False)
        
        # --- 2. Smile Bottom (LLV 120) ---
        # S1_LOW := LLV(L, 120); S1_DAY := LLVBARS(L, 120);
        res['s1_low'] = df['low'].rolling(window=120, min_periods=1).min()
        res['s1_day'] = df['low'].rolling(window=120, min_periods=1).apply(get_peak_day, raw=False) # Reuse get_peak_day logic for min
        # Correcting s1_day to be LLVBARS
        def get_llv_day(x):
            if len(x) == 0: return 0
            return len(x) - 1 - np.argmin(x.values)
        res['s1_day'] = df['low'].rolling(window=120, min_periods=1).apply(get_llv_day, raw=False)

        # S1_DONE: 坑底必须在山峰左侧，且从坑底到山峰至少有 14% 的涨幅
        res['s1_done'] = (res['s1_day'] > res['peak_day']) & \
                         ((res['peak_h'] - res['s1_low']) / res['s1_low'] > 0.14)
        
        # --- 3. Long Handle Box ---
        # IN_S2: 山峰发生在 5 到 55 天之间
        res['in_s2'] = (res['peak_day'] >= 5) & (res['peak_day'] <= 55)
        
        # BOX_LOW: 山峰以来的箱体最低点
        # This requires variable window based on peak_day, which is slow in pandas.
        # We can approximate or use a loop for accuracy as per PineScript/AmiBroker style.
        box_lows = []
        lows = df['low'].values
        peak_days = res['peak_day'].values
        for i in range(len(df)):
            pd_val = int(peak_days[i])
            if pd_val > 0:
                # LLV(L, peak_day)
                box_lows.append(np.min(lows[max(0, i-pd_val):i+1]))
            else:
                box_lows.append(lows[i])
        res['box_low'] = box_lows
        
        # BOX_SHAPE: 箱体振幅 < 25%
        res['box_shape'] = (res['peak_h'] - res['box_low']) / res['peak_h'] < 0.25
        
        # S2_DROP: 当前价格从山峰回撤至少 8%
        res['s2_drop'] = df['close'] <= res['peak_h'] * 0.92
        
        # NEAR_BOTTOM: 距离箱体最低点不超过 5% (及其上方/下方一点点)
        # NEAR_BOTTOM := C <= BOX_LOW * 1.05 AND C >= BOX_LOW * 0.98;
        res['near_bottom'] = (df['close'] <= res['box_low'] * 1.05) & \
                             (df['close'] >= res['box_low'] * 0.98)
                             
        # --- 4. MA State ---
        # S2_LEFT_BOTTOM := MA(C,5) < MA(C,20) OR C < MA(C,20);
        ma5 = df['close'].rolling(window=5).mean()
        ma20 = df['close'].rolling(window=20).mean()
        res['s2_left_bottom'] = (ma5 < ma20) | (df['close'] < ma20)
        
        # Combined Smile Flag
        res['is_smile'] = res['s1_done'] & res['in_s2'] & res['box_shape'] & \
                          res['s2_drop'] & res['near_bottom'] & res['s2_left_bottom']
        
        return res
