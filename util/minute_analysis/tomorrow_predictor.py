# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  Dict — aggregated_stats（SentimentEngine.aggregate_all 输出）
# OUTPUT: TomorrowPrediction dataclass（bullish_prob/neutral_prob/bearish_prob/confidence/reasoning/signal）
# POS:    util/minute_analysis/tomorrow_predictor.py（迁移自 check-market-sentiment/sentiment_analyzer/）
"""
Tomorrow Predictor
明日推断模块
基于形态理论推断明日市场可能性
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class TomorrowPrediction:
    """明日预测结果"""
    bullish_prob: float   # 偏强概率
    neutral_prob: float   # 震荡概率
    bearish_prob: float   # 偏弱概率
    confidence: float     # 置信度
    reasoning: List[str]  # 推理过程
    signal: str           # 综合信号


class TomorrowPredictor:
    """明日市场推断器 (基于形态理论)"""
    
    def __init__(self):
        # 因子权重 (可后续调优)
        self.weights = {
            # 正向因子 (推高偏强概率)
            'low_open_high_close': 0.15,      # 低开高走越多 → 偏强
            'v_pattern': 0.10,                  # V型反转多 → 午后有资金抄底
            'afternoon_strength': 0.12,        # 午盘强于早盘 → 资金持续流入
            'strong_consistency': 0.08,        # 高度一致 → 趋势延续
            
            # 负向因子 (推低偏强概率)
            'high_open_low_close': -0.12,      # 高开低走越多 → 偏弱
            'inverted_v': -0.10,               # 倒V型多 → 午后有资金出逃
            'morning_only_strength': -0.08,    # 只有早盘强 → 冲高回落概率大
            'sell_consistency': -0.08,         # 空头一致 → 抛压延续
            
            # 中性因子
            'flat_pattern': 0.02,             # 平淡走势多 → 无明显方向
            'oscillation': 0.00,              # 震荡整理 → 方向不明
        }
    
    def predict(self, aggregated_stats: Dict) -> TomorrowPrediction:
        """
        基于今日形态分布推断明日概率
        
        Args:
            aggregated_stats: 聚合后的市场统计数据
        
        Returns:
            明日预测结果
        """
        distribution = aggregated_stats.get('distribution', {})
        ma_stats = aggregated_stats.get('morning_afternoon', {})
        intensity = aggregated_stats.get('intensity', {})
        signal = aggregated_stats.get('signal', {})
        
        # 计算各因子得分
        factors = self._calculate_factors(
            distribution, ma_stats, intensity
        )
        
        # 计算综合得分 (基准50%)
        base_score = 0.50
        score = base_score
        
        for factor_name, value in factors.items():
            weight = self.weights.get(factor_name, 0)
            score += weight * value
        
        # 归一化到概率分布
        bullish, neutral, bearish = self._score_to_probability(score)
        
        # 生成推理过程
        reasoning = self._generate_reasoning(factors, score, distribution)
        
        # 计算置信度
        confidence = self._calculate_confidence(aggregated_stats)
        
        return TomorrowPrediction(
            bullish_prob=bullish,
            neutral_prob=neutral,
            bearish_prob=bearish,
            confidence=confidence,
            reasoning=reasoning,
            signal=self._get_signal(bullish, neutral, bearish)
        )
    
    def _calculate_factors(self, distribution: Dict, 
                          ma_stats: Dict, 
                          intensity: Dict) -> Dict[str, float]:
        """计算各因子值 (0-1 范围)"""
        factors = {}
        
        # 1. 低开高走 vs 高开低走
        low_open_high = distribution.get('低开高走', 0)
        high_open_low = distribution.get('高开低走', 0)
        
        if low_open_high + high_open_low > 0:
            factors['low_open_high_close'] = low_open_high
            factors['high_open_low_close'] = high_open_low
        else:
            factors['low_open_high_close'] = 0.1
            factors['high_open_low_close'] = 0.1
        
        # 2. V型 vs 倒V型
        v_pattern = distribution.get('V型反转', 0)
        inverted_v = distribution.get('倒V型', 0)
        
        factors['v_pattern'] = v_pattern
        factors['inverted_v'] = inverted_v
        
        # 3. 午盘 vs 早盘
        ratio = ma_stats.get('afternoon_strength_ratio', 1.0)
        
        if ratio > 1.0:
            factors['afternoon_strength'] = min(ratio - 1.0, 0.5) * 2  # 0-1
        else:
            factors['morning_only_strength'] = max(1.0 - ratio, 0.5) * 2  # 0-1
        
        # 4. 一致性
        strong_consistency = intensity.get('strong_consistency', 0.3)
        positive_ratio = intensity.get('positive_ratio', 0.5)
        
        if strong_consistency > 0.6 and positive_ratio > 0.5:
            factors['strong_consistency'] = strong_consistency
        elif strong_consistency > 0.6 and positive_ratio < 0.5:
            factors['sell_consistency'] = strong_consistency
        
        # 5. 平淡/震荡
        factors['flat_pattern'] = distribution.get('平淡走势', 0)
        factors['oscillation'] = distribution.get('震荡整理', 0)
        
        return factors
    
    def _score_to_probability(self, score: float) -> Tuple[float, float, float]:
        """将得分转换为概率分布"""
        # 使用softmax-like归一化
        # score范围: 0-1
        
        # 偏强概率
        bullish = score
        
        # 偏弱概率
        bearish = 1.0 - score
        
        # 震荡概率 (基于不确定性)
        uncertainty = 0.2  # 基础不确定性
        neutral = uncertainty
        
        # 归一化
        total = bullish + neutral + bearish
        if total == 0:
            return 0.33, 0.34, 0.33
        
        bullish = max(0.1, bullish) / total
        bearish = max(0.1, bearish) / total
        neutral = 1.0 - bullish - bearish
        
        # 确保不小于10%
        neutral = max(0.1, min(0.5, neutral))
        
        # 重新归一化
        total = bullish + neutral + bearish
        bullish /= total
        neutral /= total
        bearish /= total
        
        return bullish, neutral, bearish
    
    def _generate_reasoning(self, factors: Dict, score: float, 
                           distribution: Dict) -> List[str]:
        """生成推理过程"""
        reasoning = []
        
        # 分析低开高走/高开低走
        low_open = factors.get('low_open_high_close', 0)
        high_close = factors.get('high_open_low_close', 0)
        
        if low_open > high_close * 1.3:
            reasoning.append("低开高走形态占比高于高开低走，显示市场有'抄底'动能")
        elif high_close > low_open * 1.3:
            reasoning.append("高开低走形态占比较高，显示市场存在'高抛'压力")
        
        # 分析V型/倒V型
        v_pattern = factors.get('v_pattern', 0)
        inverted_v = factors.get('inverted_v', 0)
        
        if v_pattern > 0.15:
            reasoning.append("V型反转较多，午后资金抄底积极")
        if inverted_v > 0.15:
            reasoning.append("倒V型较多，午后资金出逃明显")
        
        # 分析午盘动能
        if 'afternoon_strength' in factors:
            reasoning.append("午盘强于早盘，资金在下午持续流入")
        if 'morning_only_strength' in factors:
            reasoning.append("只有早盘较强，存在冲高回落风险")
        
        # 一致性分析
        consistency = factors.get('strong_consistency', 0) or factors.get('sell_consistency', 0)
        if consistency > 0.7:
            reasoning.append(f"市场高度一致 ({consistency:.0%})，趋势延续概率大")
        elif consistency < 0.4:
            reasoning.append("市场分歧较大，方向不明确")
        
        # 平淡/震荡
        flat_ratio = factors.get('flat_pattern', 0)
        if flat_ratio > 0.2:
            reasoning.append(f"平淡走势较多 ({flat_ratio:.0%})，市场观望情绪较重")
        
        # 综合评价
        if score > 0.55:
            reasoning.append("综合判断：明日偏强可能性略高")
        elif score < 0.45:
            reasoning.append("综合判断：明日偏弱可能性略高")
        else:
            reasoning.append("综合判断：明日方向不明，可能震荡为主")
        
        if not reasoning:
            reasoning.append("今日市场无明显特征信号")
        
        return reasoning
    
    def _calculate_confidence(self, aggregated_stats: Dict) -> float:
        """计算置信度"""
        # 样本量影响置信度
        total_stocks = aggregated_stats.get('total_stocks', 0)
        if total_stocks < 500:
            return 0.3
        elif total_stocks < 1500:
            return 0.4
        elif total_stocks < 2500:
            return 0.5
        else:
            return 0.55
    
    def _get_signal(self, bullish: float, neutral: float, 
                    bearish: float) -> str:
        """获取综合信号"""
        if bullish > 0.45 and bullish > bearish:
            return "偏强"
        elif bearish > 0.45 and bearish > bullish:
            return "偏弱"
        else:
            return "震荡"
    
    def get_probability_description(self, prediction: TomorrowPrediction) -> str:
        """获取概率描述"""
        return (
            f"上涨/偏强: {prediction.bullish_prob:.1%} | "
            f"震荡: {prediction.neutral_prob:.1%} | "
            f"下跌/偏弱: {prediction.bearish_prob:.1%}"
        )
