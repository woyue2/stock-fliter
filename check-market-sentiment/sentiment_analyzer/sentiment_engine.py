"""
Sentiment Engine
情绪计算核心模块
"""

from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from collections import defaultdict


# 形态中英文映射
PATTERN_NAMES = {
    'single_up': '单边上涨',
    'single_down': '单边下跌',
    'v_pattern': 'V型反转',
    'inverted_v': '倒V型',
    'high_open_low_close': '高开低走',
    'low_open_high_close': '低开高走',
    'oscillation': '震荡整理',
    'flat': '平淡走势'
}


class SentimentEngine:
    """市场情绪计算引擎"""
    
    def __init__(self, num_minutes: int = 240):
        """
        Args:
            num_minutes: 每日交易分钟数 (默认240)
        """
        self.num_minutes = num_minutes
        self.morning_end = 120  # 早盘结束分钟数
    
    def calculate_pattern_distribution(self, stocks: List[Dict]) -> Dict[str, float]:
        """
        计算形态分布
        
        Args:
            stocks: 股票数据列表
        
        Returns:
            各形态占比 {pattern_name: ratio}
        """
        pattern_counts = defaultdict(int)
        
        for stock in stocks:
            pattern = stock.get('pattern', 'unknown')
            pattern_counts[pattern] += 1
        
        total = len(stocks)
        distribution = {}
        
        for pattern, count in pattern_counts.items():
            name = PATTERN_NAMES.get(pattern, pattern)
            distribution[name] = count / total
        
        return distribution
    
    def calculate_morning_afternoon_stats(self, stocks: List[Dict]) -> Dict[str, float]:
        """
        计算早盘vs午盘动能差异
        
        Args:
            stocks: 股票数据列表
        
        Returns:
            早盘午盘统计
        """
        morning_returns = []
        afternoon_returns = []
        total_returns = []
        
        for stock in stocks:
            df = stock['data']
            
            if len(df) >= self.num_minutes:
                morning = df.iloc[:self.morning_end]['return'].sum()
                afternoon = df.iloc[self.morning_end:]['return'].sum()
                total = df['return'].sum()
                
                morning_returns.append(morning)
                afternoon_returns.append(afternoon)
                total_returns.append(total)
        
        return {
            'morning_avg': np.mean(morning_returns) if morning_returns else 0,
            'afternoon_avg': np.mean(afternoon_returns) if afternoon_returns else 0,
            'total_avg': np.mean(total_returns) if total_returns else 0,
            'morning_std': np.std(morning_returns) if morning_returns else 0,
            'afternoon_std': np.std(afternoon_returns) if afternoon_returns else 0,
            'afternoon_strength_ratio': (
                np.mean(afternoon_returns) / max(abs(np.mean(morning_returns)), 0.0001)
                if afternoon_returns and morning_returns else 1.0
            )
        }
    
    def calculate_intensity_indicators(self, stocks: List[Dict]) -> Dict[str, float]:
        """
        计算强度指标
        
        Args:
            stocks: 股票数据列表
        
        Returns:
            强度指标
        """
        # 获取所有股票的收益率
        returns = [stock['returns'].iloc[-1] for stock in stocks]
        returns = sorted(returns)
        
        n = len(returns)
        if n == 0:
            return {}
        
        # 强势股和弱势股
        top_10_percent = returns[int(n * 0.9):]
        bottom_10_percent = returns[:int(n * 0.1)]
        
        # 计算一致性 (同方向股票占比)
        positive = sum(1 for r in returns if r > 0.005)  # 涨超0.5%
        negative = sum(1 for r in returns if r < -0.005)  # 跌超0.5%
        neutral = n - positive - negative
        
        return {
            'top_10_avg': np.mean(top_10_percent) if top_10_percent else 0,
            'bottom_10_avg': np.mean(bottom_10_percent) if bottom_10_percent else 0,
            'positive_ratio': positive / n,
            'negative_ratio': negative / n,
            'neutral_ratio': neutral / n,
            'strong_consistency': max(positive, negative) / n,  # 主导方向占比
            'return_skewness': pd.Series(returns).skew(),  # 收益率偏度
            'return_kurtosis': pd.Series(returns).kurtosis()  # 峰度
        }
    
    def calculate_volume_pattern(self, stocks: List[Dict]) -> Dict[str, float]:
        """
        计算成交量模式
        
        Args:
            stocks: 股票数据列表
        
        Returns:
            成交量模式
        """
        morning_volumes = []
        afternoon_volumes = []
        
        for stock in stocks:
            df = stock['data']
            if len(df) >= self.num_minutes and 'volume' in df.columns:
                morning_vol = df.iloc[:self.morning_end]['volume'].sum()
                afternoon_vol = df.iloc[self.morning_end:]['volume'].sum()
                morning_volumes.append(morning_vol)
                afternoon_volumes.append(afternoon_vol)
        
        if not morning_volumes:
            return {}
        
        return {
            'morning_volume_avg': np.mean(morning_volumes),
            'afternoon_volume_avg': np.mean(afternoon_volumes),
            'volume_ratio_afternoon_morning': (
                np.mean(afternoon_volumes) / np.mean(morning_volumes)
                if np.mean(morning_volumes) > 0 else 1.0
            )
        }
    
    def detect_market_signal(self, stats: Dict) -> Dict[str, any]:
        """
        检测市场信号
        
        Args:
            stats: 聚合统计数据
        
        Returns:
            市场信号
        """
        signals = []
        confidence = 0
        
        # 信号1: 强势股占比
        if stats.get('positive_ratio', 0) > 0.6:
            signals.append('市场偏强')
            confidence += 0.15
        elif stats.get('positive_ratio', 0) < 0.4:
            signals.append('市场偏弱')
            confidence += 0.15
        
        # 信号2: 低开高走 vs 高开低走
        distribution = stats.get('distribution', {})
        low_open_high = distribution.get('低开高走', 0)
        high_open_low = distribution.get('高开低走', 0)
        
        if low_open_high > high_open_low * 1.5:
            signals.append('抄底动能强')
            confidence += 0.1
        elif high_open_low > low_open_high * 1.5:
            signals.append('抛压较重')
            confidence += 0.1
        
        # 信号3: 午盘vs早盘
        ma_stats = stats.get('morning_afternoon', {})
        if ma_stats.get('afternoon_strength_ratio', 1) > 1.2:
            signals.append('午盘资金持续流入')
            confidence += 0.1
        elif ma_stats.get('afternoon_strength_ratio', 1) < 0.8:
            signals.append('午盘资金出逃')
            confidence += 0.1
        
        # 信号4: 一致性
        strong_consistency = stats.get('intensity', {}).get('strong_consistency', 0)
        if strong_consistency > 0.7:
            signals.append('高度一致')
            confidence += 0.1
        elif strong_consistency < 0.4:
            signals.append('分歧较大')
            confidence += 0.1
        
        return {
            'signals': signals,
            'confidence': min(confidence, 0.6)  # 最大置信度60% (单日数据限制)
        }
    
    def aggregate_all(self, stocks: List[Dict], patterns: Dict[str, str]) -> Dict:
        """
        聚合所有情绪指标
        
        Args:
            stocks: 股票数据列表
            patterns: 形态分析结果 {code: pattern_name}
        
        Returns:
            完整聚合数据
        """
        # 为每只股票添加形态
        for stock in stocks:
            stock['pattern'] = patterns.get(stock['code'], 'unknown')
        
        distribution = self.calculate_pattern_distribution(stocks)
        ma_stats = self.calculate_morning_afternoon_stats(stocks)
        intensity = self.calculate_intensity_indicators(stocks)
        volume = self.calculate_volume_pattern(stocks)
        
        stats = {
            'distribution': distribution,
            'morning_afternoon': ma_stats,
            'intensity': intensity,
            'volume': volume
        }
        
        signal = self.detect_market_signal(stats)
        
        return {
            'total_stocks': len(stocks),
            'distribution': distribution,
            'morning_afternoon': ma_stats,
            'intensity': intensity,
            'volume': volume,
            'signal': signal
        }
