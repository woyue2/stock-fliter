# util/minute_analysis/CLAUDE.md

[PROTOCOL]: 变更时更新此头部，然后检查父级 /CLAUDE.md

## 模块定位

纯算法包：**分钟级行情分析**。从 `check-market-sentiment/` 提取精华（2026-03-04 Phase 0）。

**原则**：
- 只依赖标准库、numpy、pandas，**绝不 import check-* 模块**（防循环依赖）
- 无 IO、无网络请求（DataLoader 除外，但只做文件读取）
- 可被任意 `check-*` 模块安全引入

## 成员清单

| 文件 | 类 | 职责 |
|------|----|------|
| `__init__.py` | — | 包入口，暴露所有公开类 |
| `sentiment_engine.py` | `SentimentEngine` | 市场情绪聚合计算（形态分布/早盘午盘/强度/成量）|
| `tomorrow_predictor.py` | `TomorrowPredictor`, `TomorrowPrediction` | 基于形态理论推断明日概率 |
| `minute_pattern_analyzer.py` | `MinutePatternAnalyzer`, `MinuteDataLoader` | 240维分钟向量形态分析 |
| `pattern_analyzer.py` | `PatternAnalyzer` | 日K经典形态分类（8种形态） |
| `data_loader.py` | `DataLoader` | 分钟数据并行加载（含日期发现/ThreadPoolExecutor）|

## 典型用法

```python
from util.minute_analysis import MinutePatternAnalyzer, SentimentEngine, TomorrowPredictor

analyzer = MinutePatternAnalyzer()
result = analyzer.analyze_single_stock(minute_df)  # → {pattern_code, features, ...}
```

## 迁移来源（已删除）

原 `check-market-sentiment/sentiment_analyzer/` 和根目录精华文件，
删除的废弃文件：batch_analyze.py、report_generator.py、pattern_html_reporter.py 等。
