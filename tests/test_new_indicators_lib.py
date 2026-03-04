# -*- coding: utf-8 -*-
"""
Test script for new indicators in util/indicators_lib.py
"""
import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from util.indicators_lib import TechnicalIndicators

class TestNewIndicators(unittest.TestCase):
    
    def setUp(self):
        # Create dates
        self.dates = pd.date_range(start="2023-01-01", periods=100)
    
    def test_calculate_max_drawdown(self):
        # Case 1: No drawdown (strictly increasing)
        prices = np.array([10, 11, 12, 13, 14, 15])
        dd = TechnicalIndicators.calculate_max_drawdown(prices)
        self.assertEqual(dd, 0.0)
        
        # Case 2: 50% drawdown
        prices = np.array([10, 20, 10, 15])
        dd = TechnicalIndicators.calculate_max_drawdown(prices)
        self.assertEqual(dd, -0.5)
        
    def test_calculate_rolling_max_drawdown(self):
        prices = pd.Series([10, 20, 10, 15, 30, 15], index=self.dates[:6])
        # Window 3
        # [10, 20, 10] -> Max 20, Min 10, DD -0.5
        # [20, 10, 15] -> Max 20, Min 10, DD -0.5
        # [10, 15, 30] -> Max 30, Min 10 (Wait, rolling starts from window end)
        
        rolling_dd = TechnicalIndicators.calculate_rolling_max_drawdown(prices, window=3)
        # First 2 should be NaN (min_periods=3)
        self.assertTrue(pd.isna(rolling_dd.iloc[0]))
        self.assertTrue(pd.isna(rolling_dd.iloc[1]))
        
        # 3rd: [10, 20, 10] -> Peak 20, Drop to 10 -> -0.5
        self.assertAlmostEqual(rolling_dd.iloc[2], -0.5)
        
    def test_check_steady_uptrend(self):
        # Create a steady uptrend scenario
        # Linear growth with small noise
        prices = np.linspace(10, 100, 100)
        close = pd.Series(prices, index=self.dates)
        
        result = TechnicalIndicators.check_steady_uptrend(close)
        
        # Check if the last point is considered steady uptrend
        # Since it's perfectly linear, MAs should be ordered correctly
        # MA5 > MA10 > MA20 > MA30 > MA60 (eventually)
        
        # We need enough data points for MA60
        self.assertTrue("steady_uptrend" in result.columns)
        self.assertTrue(result["steady_uptrend"].iloc[-1])
        
    def test_calculate_td_sequence(self):
        # Create a TD buy setup (9 consecutive closes lower than 4 bars ago)
        # Sequence logic: close[i] < close[i-4]
        
        # We need to ensure close[i] < close[i-4] for i from 4 to 12 (9 bars)
        # i=4: 90 < 100
        # i=5: 90 < 100
        # i=6: 90 < 100
        # i=7: 90 < 100
        # i=8: 80 < 90
        # ...
        
        vals = [100] * 20
        # i=0..3: 100
        # i=4..7: 90
        for i in range(4, 8):
            vals[i] = 90
        # i=8..11: 80
        for i in range(8, 12):
            vals[i] = 80
        # i=12: 70
        vals[12] = 70
        
        close = pd.Series(vals, index=self.dates[:20])
        td_seq = TechnicalIndicators.calculate_td_sequence(close)
        
        # i=4: 90 < 100 -> 1
        self.assertEqual(td_seq.iloc[4], 1)
        # i=8: 80 < 90 -> 5
        self.assertEqual(td_seq.iloc[8], 5)
        # i=12: 70 < 80 -> 9
        self.assertEqual(td_seq.iloc[12], 9)
        
        # Test unbounded growth (i=13..16: 60)
        # i=13: 60 < 80 -> 10
        # i=14: 60 < 80 -> 11
        # i=15: 60 < 80 -> 12
        # i=16: 60 < 70 -> 13
        for i in range(13, 17):
            vals[i] = 60
        close_long = pd.Series(vals, index=self.dates[:20])
        td_seq_long = TechnicalIndicators.calculate_td_sequence(close_long)
        self.assertEqual(td_seq_long.iloc[13], 10)
        self.assertEqual(td_seq_long.iloc[16], 13)


    def test_resample_ohlcv(self):
        # Create daily data for 2 weeks
        dates = pd.date_range(start="2023-01-01", periods=14)
        df = pd.DataFrame({
            "date": dates,
            "open": [10] * 14,
            "high": [20] * 14,
            "low": [5] * 14,
            "close": [15] * 14,
            "volume": [1000] * 14
        })
        
        resampled = TechnicalIndicators.resample_ohlcv(df, "W")
        # Should have at least 2 weeks (depending on start day, 2023-01-01 is Sunday)
        # Pandas resample 'W' usually ends on Sunday.
        
        self.assertFalse(resampled.empty)
        self.assertTrue("open" in resampled.columns)
        self.assertTrue("volume" in resampled.columns)
        
if __name__ == "__main__":
    unittest.main()
