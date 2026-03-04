# -*- coding: utf-8 -*-
"""
技术指标库 (Technical Indicators Library)
项目统一的技术指标计算库
"""
import pandas as pd
import numpy as np


class TechnicalIndicators:
    """技术指标计算类"""

    @staticmethod
    def calculate_ma(data: pd.Series, period: int) -> pd.Series:
        """计算移动平均线"""
        return data.rolling(window=period).mean()

    @staticmethod
    def calculate_macd(data: pd.Series, fast_period=12, slow_period=26, signal_period=9):
        """
        计算MACD指标
        Returns: (MACD线, 信号线, 柱状图)
        """
        # 计算EMA
        ema_fast = data.ewm(span=fast_period, adjust=False).mean()
        ema_slow = data.ewm(span=slow_period, adjust=False).mean()

        # MACD线
        macd_line = ema_fast - ema_slow

        # 信号线
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()

        # 柱状图
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    @staticmethod
    def check_macd_golden_cross(close_prices: pd.Series, fast_period=12, slow_period=26, signal_period=9) -> bool:
        """检测MACD金叉"""
        if len(close_prices) < slow_period + signal_period + 1:
            return False

        macd_line, signal_line, _ = TechnicalIndicators.calculate_macd(
            close_prices, fast_period, slow_period, signal_period
        )

        # 获取最近两天的数据
        macd_recent = macd_line.iloc[-2:]
        signal_recent = signal_line.iloc[-2:]

        if pd.isna(macd_recent.iloc[0]) or pd.isna(signal_recent.iloc[0]):
            return False

        # 检查金叉: 昨天快线<=慢线, 今天快线>慢线
        golden_cross = (
            macd_recent.iloc[0] <= signal_recent.iloc[0] and
            macd_recent.iloc[1] > signal_recent.iloc[1]
        )

        return golden_cross

    @staticmethod
    def check_macd_golden_cross_below_zero(close_prices: pd.Series, fast_period=12, slow_period=26, signal_period=9) -> bool:
        """检测MACD零轴下金叉 (更可靠的买入信号)"""
        if not TechnicalIndicators.check_macd_golden_cross(close_prices, fast_period, slow_period, signal_period):
            return False

        macd_line, _, _ = TechnicalIndicators.calculate_macd(close_prices, fast_period, slow_period, signal_period)

        # 检查金叉时MACD线是否在零轴下方
        return macd_line.iloc[-1] < 0

    @staticmethod
    def check_volume_breakout(close_prices: pd.Series, volumes: pd.Series, lookback_period=20, volume_multiplier=1.5) -> bool:
        """
        检测放量突破
        条件: 
        1. 价格突破过去N天的最高价
        2. 成交量大于过去N天平均成交量的M倍
        """
        if len(close_prices) < lookback_period + 1:
            return False

        # 计算回看期间的最高价（阻力位）
        resistance = close_prices.iloc[-lookback_period-1:-1].max()

        # 获取最新数据
        latest_close = close_prices.iloc[-1]
        latest_volume = volumes.iloc[-1]

        # 计算平均成交量 (不包含今天)
        avg_volume = volumes.iloc[-lookback_period-1:-1].mean()

        if pd.isna(resistance) or pd.isna(avg_volume) or avg_volume == 0:
            return False

        # 检查是否突破且放量
        breakout = latest_close > resistance  # 突破
        high_volume = latest_volume > avg_volume * volume_multiplier  # 放量

        return bool(breakout and high_volume)

    @staticmethod
    def calculate_max_drawdown(values: np.ndarray) -> float:
        """
        计算最大回撤
        """
        if values.size == 0:
            return 0.0
        running_max = np.maximum.accumulate(values)
        # 避免除以0
        with np.errstate(divide='ignore', invalid='ignore'):
            drawdown = (values - running_max) / running_max
            
        drawdown = np.nan_to_num(drawdown) # 处理 NaN/Inf
        return float(np.min(drawdown))

    @staticmethod
    def calculate_rolling_max_drawdown(series: pd.Series, window: int) -> pd.Series:
        """
        计算滚动最大回撤
        """
        def _mdd(arr: np.ndarray) -> float:
            return TechnicalIndicators.calculate_max_drawdown(arr)

        return series.rolling(window=window, min_periods=window).apply(_mdd, raw=True)

    @staticmethod
    def check_steady_uptrend(
        close_prices: pd.Series, 
        ma_windows=(5, 10, 20, 30), 
        ma_long=60,
        slope_lookback_short=5,
        slope_lookback_long=10,
        drawdown_lookback=60,
        max_drawdown=0.08
    ) -> pd.DataFrame:
        """
        检测MAxRSIx6U1D形态
        
        Returns:
            DataFrame 包含中间计算结果和最终标志 'steady_uptrend'
        """
        close = close_prices.astype(float)
        df_res = pd.DataFrame(index=close.index)
        
        # 计算均线
        ma5 = TechnicalIndicators.calculate_ma(close, ma_windows[0])
        ma10 = TechnicalIndicators.calculate_ma(close, ma_windows[1])
        ma20 = TechnicalIndicators.calculate_ma(close, ma_windows[2])
        ma30 = TechnicalIndicators.calculate_ma(close, ma_windows[3])
        ma60 = TechnicalIndicators.calculate_ma(close, ma_long) if len(close) >= ma_long else pd.Series(index=close.index, dtype=float)

        # 计算斜率 (当前均线 - N天前均线)
        slope20 = ma20 - ma20.shift(slope_lookback_short)
        slope30 = ma30 - ma30.shift(slope_lookback_short)
        slope60 = ma60 - ma60.shift(slope_lookback_long)

        # 1. 均线多头排列
        order_ok = (ma5 > ma10) & (ma10 > ma20) & (ma20 > ma30)
        
        # 2. 均线斜率向上
        slope_ok = (slope20 > 0) & (slope30 > 0)
        if not ma60.empty and not ma60.isna().all():
            slope_ok = slope_ok & (slope60 > 0)

        # 3. 价格站上均线
        price_above = (close > ma20) & (close > ma30)
        if not ma60.empty and not ma60.isna().all():
             price_above = price_above & (close > ma60)

        # 4. 低回撤
        drawdown = TechnicalIndicators.calculate_rolling_max_drawdown(close, drawdown_lookback)
        drawdown_ok = drawdown >= -max_drawdown

        # 综合判断
        steady_uptrend = order_ok & slope_ok & price_above & drawdown_ok

        # 保存结果
        df_res["ma5"] = ma5
        df_res["ma10"] = ma10
        df_res["ma20"] = ma20
        df_res["ma30"] = ma30
        df_res["ma60"] = ma60
        df_res["slope20"] = slope20
        df_res["slope30"] = slope30
        df_res["slope60"] = slope60
        df_res["drawdown_60"] = drawdown
        df_res["steady_uptrend"] = steady_uptrend
        
        return df_res

    @staticmethod
    def calculate_td_sequence(close_prices: pd.Series) -> pd.Series:
        """
        计算TD序列 (Tom DeMark Sequential)
        
        Returns:
            Series 包含TD计数 (正数为上涨序列，这里只实现下跌买入序列通常用正数表示下跌计数，或者根据具体策略)
            
            在此实现中，逻辑参照 check-td/analyzers/td_analyzer.py:
            如果 close[i] < close[i-4], 计数+1, 否则重置为0
            返回的序列是下跌计数序列（寻找底部）
        """
        sequence = np.zeros(len(close_prices), dtype=int)
        values = close_prices.values
        current = 0
        
        for i in range(len(values)):
            if i < 4:
                sequence[i] = 0
                continue
            
            if values[i] < values[i - 4]:
                current += 1
            else:
                current = 0
            sequence[i] = current
            
        return pd.Series(sequence, index=close_prices.index)

    @staticmethod
    def calculate_parkinson_volatility(high: pd.Series, low: pd.Series, window: int = 20) -> float:
        """
        计算 Parkinson 波动率 (基于高低价范围)
        公式: V = sqrt(1 / (4 * n * ln(2)) * sum(ln(Hi/Li)^2))
        """
        if len(high) < window or len(low) < window:
            return 0.0
        
        # 取最近 window 天的数据
        h = high.tail(window).astype(float)
        l = low.tail(window).astype(float)
        
        # 避免除以0
        l = l.replace(0, np.nan)
        
        # 计算 ln(H/L)^2
        log_range_sq = np.log(h / l) ** 2
        
        # 计算 Parkinson 波动率
        sum_sq = log_range_sq.sum()
        parkinson_daily = np.sqrt(sum_sq / (4 * window * np.log(2)))
        
        # 年化 (假设一年 250 个交易日)
        return float(parkinson_daily * np.sqrt(250))

    @staticmethod
    def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
        """
        重采样 OHLCV 数据
        rule: 'W' (周), 'ME' (月), etc.
        """
        if df.empty:
            return pd.DataFrame()
        
        # 确保 date 是索引
        if "date" in df.columns:
            df = df.set_index("date")
            # 确保索引是 datetime 类型
            df.index = pd.to_datetime(df.index)
            
        resampled = df.resample(rule).agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        })
        # 去除无效行并重置索引
        resampled = resampled.dropna().reset_index()
        return resampled
