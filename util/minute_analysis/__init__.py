# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""
util/minute_analysis — 分钟级行情分析算法包

迁移自 check-market-sentiment/（2026-03-04 Phase 0 重构）
包含纯算法模块，无 IO 依赖，可被任意 check-* 模块引入。

模块成员：
  sentiment_engine.py      — 市场情绪计算引擎 (SentimentEngine)
  tomorrow_predictor.py    — 明日推断模块 (TomorrowPredictor)
  minute_pattern_analyzer.py — 240维分钟向量形态分析器 (MinutePatternAnalyzer)
  pattern_analyzer.py      — 日K经典形态分析器 (PatternAnalyzer)
  data_loader.py           — 分钟数据加载器，含并行加载/logging (DataLoader)
"""

from .sentiment_engine import SentimentEngine
from .tomorrow_predictor import TomorrowPredictor, TomorrowPrediction
from .minute_pattern_analyzer import MinutePatternAnalyzer, MinuteDataLoader
from .pattern_analyzer import PatternAnalyzer
from .data_loader import DataLoader

__all__ = [
    "SentimentEngine",
    "TomorrowPredictor",
    "TomorrowPrediction",
    "MinutePatternAnalyzer",
    "MinuteDataLoader",
    "PatternAnalyzer",
    "DataLoader",
]
