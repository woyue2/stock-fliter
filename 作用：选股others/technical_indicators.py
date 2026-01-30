# -*- coding: utf-8 -*-
"""
技术指标计算模块
包含：均线、MACD、RSI、成交量指标
"""
import numpy as np
import pandas as pd


class TechnicalIndicators:
    """技术指标计算类"""

    @staticmethod
    def calculate_ma(data, period):
        """
        计算移动平均线

        Parameters:
        -----------
        data : pd.Series
            价格数据（通常为收盘价）
        period : int
            周期

        Returns:
        --------
        pd.Series
            移动平均线
        """
        return data.rolling(window=period).mean()

    @staticmethod
    def check_ma_golden_cross(close_prices, short_period=5, long_period=20):
        """
        检测均线金叉（买入信号）

        Parameters:
        -----------
        close_prices : pd.Series
            收盘价序列
        short_period : int
            短期均线周期（默认5日）
        long_period : int
            长期均线周期（默认20日）

        Returns:
        --------
        bool
            是否出现金叉
        """
        if len(close_prices) < long_period + 1:
            return False

        ma_short = TechnicalIndicators.calculate_ma(close_prices, short_period)
        ma_long = TechnicalIndicators.calculate_ma(close_prices, long_period)

        # 获取最近两天的数据
        short_recent = ma_short.iloc[-2:]
        long_recent = ma_long.iloc[-2:]

        # 检查金叉：昨日短线下穿长线（或相等），今日短线上穿长线
        if pd.isna(short_recent.iloc[0]) or pd.isna(long_recent.iloc[0]):
            return False

        golden_cross = (
            short_recent.iloc[0] <= long_recent.iloc[0] and
            short_recent.iloc[1] > long_recent.iloc[1]
        )

        return golden_cross

    @staticmethod
    def calculate_macd(data, fast_period=12, slow_period=26, signal_period=9):
        """
        计算MACD指标

        Parameters:
        -----------
        data : pd.Series
            收盘价序列
        fast_period : int
            快线周期（默认12）
        slow_period : int
            慢线周期（默认26）
        signal_period : int
            信号线周期（默认9）

        Returns:
        --------
        tuple
            (MACD线, 信号线, 柱状图)
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
    def check_macd_golden_cross(close_prices, fast_period=12, slow_period=26, signal_period=9):
        """
        检测MACD金叉（买入信号）

        Parameters:
        -----------
        close_prices : pd.Series
            收盘价序列
        fast_period : int
            快线周期
        slow_period : int
            慢线周期
        signal_period : int
            信号线周期

        Returns:
        --------
        bool
            是否出现MACD金叉
        """
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

        # 检查金叉
        golden_cross = (
            macd_recent.iloc[0] <= signal_recent.iloc[0] and
            macd_recent.iloc[1] > signal_recent.iloc[1]
        )

        return golden_cross

    @staticmethod
    def check_macd_golden_cross_below_zero(close_prices, fast_period=12, slow_period=26, signal_period=9):
        """
        检测MACD零轴下金叉（更可靠的买入信号）

        Parameters:
        -----------
        close_prices : pd.Series
            收盘价序列

        Returns:
        --------
        bool
            是否出现零轴下金叉
        """
        if not TechnicalIndicators.check_macd_golden_cross(close_prices, fast_period, slow_period, signal_period):
            return False

        macd_line, _, _ = TechnicalIndicators.calculate_macd(close_prices, fast_period, slow_period, signal_period)

        # 检查金叉时MACD线是否在零轴下方
        return macd_line.iloc[-1] < 0

    @staticmethod
    def calculate_rsi(data, period=14):
        """
        计算RSI指标

        Parameters:
        -----------
        data : pd.Series
            收盘价序列
        period : int
            周期（默认14）

        Returns:
        --------
        pd.Series
            RSI值序列
        """
        # 计算价格变化
        delta = data.diff()

        # 分离上涨和下跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # 计算平均涨跌幅
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # 计算RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def check_rsi_oversold_turnup(close_prices, period=14, oversold_threshold=30):
        """
        检测RSI超卖后拐头向上（买入信号）

        Parameters:
        -----------
        close_prices : pd.Series
            收盘价序列
        period : int
            RSI周期
        oversold_threshold : float
            超卖阈值（默认30）

        Returns:
        --------
        bool
            是否出现超卖后拐头
        """
        if len(close_prices) < period + 2:
            return False

        rsi = TechnicalIndicators.calculate_rsi(close_prices, period)

        # 获取最近三天的RSI值
        rsi_recent = rsi.iloc[-3:]

        if pd.isna(rsi_recent).any():
            return False

        # 检查是否超卖后拐头
        # 前天或昨天RSI低于阈值，今天RSI高于前天/昨天
        oversold_before = rsi_recent.iloc[0] < oversold_threshold or rsi_recent.iloc[1] < oversold_threshold
        turning_up = rsi_recent.iloc[2] > rsi_recent.iloc[1] and rsi_recent.iloc[2] > rsi_recent.iloc[0]

        return oversold_before and turning_up

    @staticmethod
    def check_volume_breakout(close_prices, volumes, lookback_period=20, volume_multiplier=1.5):
        """
        检测底部放量突破（买入信号）

        Parameters:
        -----------
        close_prices : pd.Series
            收盘价序列
        volumes : pd.Series
            成交量序列
        lookback_period : int
            回看周期（计算阻力位）
        volume_multiplier : float
            成交量放大倍数

        Returns:
        --------
        bool
            是否出现放量突破
        """
        if len(close_prices) < lookback_period + 1:
            return False

        # 计算回看期间的最高价（阻力位）
        resistance = close_prices.iloc[-lookback_period-1:-1].max()

        # 获取最新数据
        latest_close = close_prices.iloc[-1]
        latest_volume = volumes.iloc[-1]

        # 计算平均成交量
        avg_volume = volumes.iloc[-lookback_period-1:-1].mean()

        # 检查是否突破且放量
        breakout = latest_close > resistance  # 突破
        high_volume = latest_volume > avg_volume * volume_multiplier  # 放量

        return breakout and high_volume

    @staticmethod
    def calculate_td_sequence(close_prices):
        """
        计算TD序列（九底/九顶）

        Parameters:
        -----------
        close_prices : pd.Series
            收盘价序列

        Returns:
        --------
        dict
            {
                'buy_sequence': 买入序列数组,
                'current_buy': 当前买入序列值,
                'is_buy_setup': 是否完成买入设置(九底),
                'is_buy_setup_8': 是否达到8底,
                'is_buy_setup_7': 是否达到7底
            }
        """
        if len(close_prices) < 5:
            return {
                'buy_sequence': [],
                'current_buy': 0,
                'is_buy_setup': False,
                'is_buy_setup_8': False,
                'is_buy_setup_7': False
            }

        # 初始化买入序列数组
        buy_sequence = [0] * len(close_prices)
        buy_count = 0

        for i in range(4, len(close_prices)):
            # TD买入设置（九底）：收盘价低于4根K线前的收盘价
            if close_prices.iloc[i] < close_prices.iloc[i-4]:
                buy_count += 1
                if buy_count > 9:  # 超过9后重置为1
                    buy_count = 1
            else:
                buy_count = 0

            buy_sequence[i] = buy_count

        # 当前状态
        current_buy = buy_sequence[-1] if buy_sequence else 0

        return {
            'buy_sequence': buy_sequence,
            'current_buy': current_buy,
            'is_buy_setup': current_buy >= 9,  # 9底
            'is_buy_setup_8': current_buy >= 8,  # 8底及以上
            'is_buy_setup_7': current_buy >= 7   # 7底及以上
        }

    @staticmethod
    def check_td_buy_setup(close_prices, min_count=9):
        """
        检测TD买入设置（九底/八底/七底）

        Parameters:
        -----------
        close_prices : pd.Series
            收盘价序列
        min_count : int
            最小计数（9=九底，8=八底，7=七底）

        Returns:
        --------
        bool
            是否达到指定买入设置
        """
        if len(close_prices) < 9:
            return False

        result = TechnicalIndicators.calculate_td_sequence(close_prices)
        current_buy = result['current_buy']

        return current_buy >= min_count

    @staticmethod
    def check_all_signals(close_prices, volumes):
        """
        检测所有买入信号（组合信号）

        Parameters:
        -----------
        close_prices : pd.Series
            收盘价序列
        volumes : pd.Series
            成交量序列

        Returns:
        --------
        dict
            各信号检测结果
        """
        # 计算TD序列
        td_result = TechnicalIndicators.calculate_td_sequence(close_prices)

        signals = {
            'ma_golden_cross': TechnicalIndicators.check_ma_golden_cross(close_prices),
            'macd_golden_cross': TechnicalIndicators.check_macd_golden_cross(close_prices),
            'macd_golden_cross_below_zero': TechnicalIndicators.check_macd_golden_cross_below_zero(close_prices),
            'rsi_oversold_turnup': TechnicalIndicators.check_rsi_oversold_turnup(close_prices),
            'volume_breakout': TechnicalIndicators.check_volume_breakout(close_prices, volumes),
            'td_9': td_result['is_buy_setup'],  # 9底
            'td_8': td_result['is_buy_setup_8'],  # 8底及以上
            'td_7': td_result['is_buy_setup_7'],  # 7底及以上
            'td_count': td_result['current_buy']  # 当前TD计数
        }

        # 计算满足的信号数量（不包括TD相关指标）
        signals['signal_count'] = sum([v for k, v in signals.items() if k not in ['td_count', 'td_9', 'td_8', 'td_7']])

        return signals
