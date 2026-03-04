# Pandas 纯向量化底层优化记录

在针对低配置（2核2G内存）的服务器优化过程中，我们实施了一系列基于 Pandas 的纯 C 层**向量化操作**。相比于直接用 Python `for` 循环和回调整数（`apply`），这极大地释放了计算潜能并减少了内存压力。

现将本次针对大回撤运算、主力试盘运算和 TD 序列运算的核心优化变更记录如下，以备后续参考：

### 1. 连续 TD 序列计数的向量化
**痛点**：原本的 `calculate_td_sequence` 依赖 `for idx, val in enumerate(close.values)` 逐行匹配 `val < close[idx-4]`，效率低下，拖慢了日周月多线并行的筛选。
**优化方案**：利用 `shift()` 判断跌破条件，随后用神奇的 `(~cond).cumsum()` 分段技巧替代手动重置计数，实现了完全在底层 C 中完成计数的操作。
```python
@staticmethod
def calculate_td_sequence(close_prices: pd.Series) -> pd.Series:
    # 巧妙利用 cumsum 来标识连续的 True 片段
    cond = close_prices < close_prices.shift(4)
    group = (~cond).cumsum()
    sequence = cond.groupby(group).cumsum().astype(int)
    return sequence
```

### 2. 移除消耗巨大的回调 `apply` (最大回撤)
**痛点**：原本 `calculate_rolling_max_drawdown` 用 `.rolling(window=window).apply(_mdd, raw=True)`。每次步进都将切割一整个 Numpy 数组发给 Python 方法，开销极大且占用极高。
**优化方案**：放弃切片传值，采用滚动算子直接取最大值，转而把计算降维为两个序列间的算术运算(`(series - rolling_max) / rolling_max`)。
```python
@staticmethod
def calculate_rolling_max_drawdown(series: pd.Series, window: int) -> pd.Series:
    rolling_max = series.rolling(window=window, min_periods=1).max()
    daily_drawdown = (series - rolling_max) / rolling_max
    daily_drawdown = daily_drawdown.fillna(0)
    return daily_drawdown.rolling(window=window, min_periods=window).min()
```

### 3. 主力试盘业务运算去行化 (`.iloc` 替换)
**痛点**：`shipan_logic.py` 中的 `analyze_shipan_behavior` 里面，存在对尾部 45 个交易日每一日的独立 `.iloc[]` 调用和复杂的字典解析式，导致 `check-volupxyangxshipan` 这个轻量级逻辑反而拖后腿。
**优化方案**：一次性把前一日收盘价 (`shift(1)`) 挂载，并将下影线/上影线/涨停等所有乘法和 `if` 判断转换为条件级列运算掩码 (如 `max(axis=1)` 等)。
```python
# 将对45次循环的下影线判断全部转换为列际逻辑运算合并
day_range = (scan_df['high'] - scan_df['low']).clip(lower=0.01)
body = (scan_df['close'] - scan_df['open']).abs()
max_oc = scan_df[['open', 'close']].max(axis=1)
upper_shadow = scan_df['high'] - max_oc

cond_limit = (pct_chg > 7.0) & (vol > v_ma20 * 1.3)
cond_upper = (upper_shadow > body * 1.5) & (upper_shadow > day_range * 0.4) & (vol > v_ma20 * 1.5)
# ... 最后再利用掩码选取 df.loc[cond, 'shipan_type'] = "涨停"
```

这些变造都是非常“吃内存”环境下的完美退让，彻底用矩阵操作替换了标量循环，完美匹配了轻服务器的低端 CPU 性能极限。
