# 市场情绪分析 - 高开低走/低开高走检测

## ⚠️ 重要说明

### 数据源问题

当前 `stocks_index.csv` 中的股票是经过各个分析模块筛选后的结果，这些股票可能：
1. 在 `get-data/data/day/` 目录中没有对应的价格数据文件
2. 数据文件存在但日期不匹配

### 解决方案

有两种方式来分析市场情绪：

#### 方案 1：使用 selected_stocks_all.csv（推荐）

使用完整的股票列表和价格数据：

```bash
# 修改 data_loader.py 使其从 selected_stocks_all.csv 加载股票列表
# 然后从 day 目录加载价格数据
```

#### 方案 2：直接分析 day 目录中的所有股票

扫描 `get-data/data/day/` 目录中的所有 CSV 文件，直接读取价格数据。

## 功能说明

检测股票的日内交易模式：

### 模式定义

1. **高开低走** (High Open Low Close)
   - 开盘价 > 昨日收盘价（高开）
   - 收盘价 < 开盘价（低走）
   - 市场特征：开盘冲高后回落，可能表示抛压较重

2. **低开高走** (Low Open High Close)
   - 开盘价 < 昨日收盘价（低开）
   - 收盘价 > 开盘价（高走）
   - 市场特征：开盘低迷后反弹，可能表示买盘积极

3. **市场情绪指数**
   - 计算公式：`(低开高走数量 - 高开低走数量) / 总股票数 × 100`
   - 正值：市场偏强
   - 负值：市场偏弱

## 使用方法

### 基本用法

```bash
# 分析最新交易日
python main.py

# 分析指定日期
python main.py --date 2026-01-30

# 分析最近N天
python main.py --recent 5

# 分析所有可用数据
python main.py --all
```

### 参数说明

- `--date DATE`: 分析指定日期（格式：YYYY-MM-DD）
- `--recent N`: 分析最近N个交易日
- `--all`: 分析所有可用数据
- `--output DIR`: 指定输出目录（默认：output）

## 输出文件

### HTML 报告
- 文件名：`market_sentiment_YYYYMMDD_HHMMSS.html`
- 包含：
  - 市场整体概况
  - 每日市场情绪分析（多天数据时）
  - 行业分析（Top 20）
  - 股票详情（Top 100）

### CSV 报告
- 文件名：`market_sentiment_YYYYMMDD_HHMMSS.csv`
- 包含所有股票的详细数据

## 数据流程

```
stocks_index/
  └── 2026-01-30/
      └── stocks_index.csv  (股票列表，无价格数据)
            ↓
      需要从 day/ 目录加载价格数据
            ↓
get-data/data/day/
  ├── 600028.csv  (中国石化的历史价格数据)
  ├── 600036.csv  (招商银行的历史价格数据)
  └── ...
```

## 当前状态

- ✅ 支持从 `stocks_index` 目录按日期加载股票列表
- ✅ 支持多天数据分析
- ✅ 生成美观的 HTML 报告
- ⚠️ 需要解决：`stocks_index.csv` 中的股票在 `day` 目录中找不到价格数据

## 下一步计划

1. 修改数据加载逻辑，改为扫描 `day` 目录中的所有股票
2. 或者使用 `selected_stocks_all.csv` 作为股票列表
3. 添加数据缓存机制，提高加载速度
4. 支持分钟级数据分析（早盘/午盘情绪）

## 技术细节

### 前一日收盘价计算

使用 `groupby + shift` 方法：

```python
df['prev_close'] = df.groupby('code')['close'].shift(1)
```

这样可以正确处理：
- 多只股票的数据
- 不同日期的数据
- 缺失的交易日

### 模式识别

```python
# 开盘涨跌幅
open_change_pct = (open - prev_close) / prev_close * 100

# 日内涨跌幅
intraday_change_pct = (close - open) / open * 100

# 判断模式
if open_change_pct > 0.5 and intraday_change_pct < -0.5:
    pattern = "高开低走"
elif open_change_pct < -0.5 and intraday_change_pct > 0.5:
    pattern = "低开高走"
```

## 相关文档

- [wdm_sentiment.md](wdm_sentiment.md) - 市场情绪分析伪代码
- [DATA_FLOW.md](../get-data/DATA_FLOW.md) - 完整数据流程文档
