# 市场情绪分析模块 - 更新日志

## 2026-01-31 修复

### 问题描述
程序在只加载1天数据时，无法计算前一日收盘价（prev_close），导致所有记录的prev_close都是NaN，进而导致分析失败。

### 根本原因
- 计算涨跌幅需要"前一日收盘价"
- 如果只加载当天数据，就没有"前一天"的数据来计算prev_close
- 使用`groupby().shift(1)`时，每只股票只有1条记录，shift后全部为NaN

### 解决方案
修改默认行为，从加载1天数据改为加载最近2天数据：

**修改文件**: `check-market-sentiment/main.py`

**修改位置**: 第130-135行

**修改内容**:
```python
# 修改前
else:
    # 默认：分析最新交易日
    print("分析最新交易日")
    market_data = loader.load_latest_date(show_progress=True)

# 修改后
else:
    # 默认：分析最近2天（需要前一日数据来计算涨跌幅）
    print("分析最新交易日（加载最近2天数据以计算涨跌幅）")
    market_data = loader.load_recent_days(2, show_progress=True)
```

### 测试结果
✅ 成功加载5009只股票的数据
✅ 成功计算前一日收盘价
✅ 成功生成市场情绪分析报告
✅ CSV文件包含5010行（1行标题 + 5009条数据）

### 输出文件
- CSV报告: `market_sentiment_YYYYMMDD_HHMMSS.csv`
- HTML报告: `market_sentiment_YYYYMMDD_HHMMSS.html`

### 数据字段
- code: 股票代码
- name: 股票名称
- date: 交易日期
- open: 开盘价
- high: 最高价
- low: 最低价
- close: 收盘价
- intraday_change_pct: 日内涨跌幅（%）
- amplitude: 振幅（%）
- pattern: 形态（高开低走、低开高走、平开平走等）
- strength: 强度（强、中、弱）
- industry: 所属行业

### 命令行参数
程序支持以下参数：
- `--recent N`: 分析最近N个交易日
- `--date YYYY-MM-DD`: 分析指定日期
- `--all`: 分析所有可用数据

### 注意事项
1. 默认情况下，程序会加载最近2天的数据，但只分析最新一天的市场情绪
2. 第2天的数据仅用于计算第1天的前一日收盘价
3. 如果需要分析多天的市场情绪趋势，可以使用`--recent N`参数

