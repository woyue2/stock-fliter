# 数据模型

## 概述
项目使用CSV格式存储股票数据，Excel格式输出分析结果。

---

## 数据存储

### 股票数据文件

**存储路径:** `data/` 目录下的CSV文件

**文件命名格式:**
- 股票列表: `stock_list_YYYYMMDD_HHMMSS.csv`
- 日K数据: `{股票代码}_daily_YYYYMMDD_HHMMSS.csv`
- 周K数据: `{股票代码}_weekly_YYYYMMDD_HHMMSS.csv`
- 月K数据: `{股票代码}_monthly_YYYYMMDD_HHMMSS.csv`

### 日K数据结构

| 字段 | 类型 | 说明 |
|------|------|------|
| date | string | 日期（YYYY-MM-DD） |
| open | float | 开盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| close | float | 收盘价 |
| volume | integer | 成交量 |

---

## 输出数据

### 综合选股结果

**Excel文件名格式:** `all_results_YYYYMMDD_HHMMSS.xlsx` 和 `qualified_*signals_YYYYMMDD_HHMMSS.xlsx`

**结果字段:**
| 字段 | 类型 | 说明 |
|------|------|------|
| 代码 | string | 股票代码 |
| 名称 | string | 股票名称 |
| 日期 | string | 最新交易日期 |
| 收盘价 | float | 最新收盘价 |
| 涨跌幅(%) | float | 最新涨跌幅 |
| 成交量 | integer | 最新成交量 |
| 信号数 | integer | 满足的信号总数 |
| 均线金叉 | boolean | ✓表示满足 |
| MACD金叉 | boolean | ✓表示满足 |
| MACD零轴下金叉 | boolean | ✓表示满足 |
| RSI超卖拐头 | boolean | ✓表示满足 |
| 放量突破 | boolean | ✓表示满足 |
| TD序列 | integer | 当前TD计数 |
| 9底 | boolean | ✓表示达到9底 |
| 8底 | boolean | ✓表示达到8底及以上 |
| 7底 | boolean | ✓表示达到7底及以上 |

---

### TD序列结果

**Excel文件名格式:** `td_all_results_YYYYMMDD_HHMMSS.xlsx` 和 `td_qualified_*plus_YYYYMMDD_HHMMSS.xlsx`

**结果字段:**
| 字段 | 类型 | 说明 |
|------|------|------|
| 代码 | string | 股票代码 |
| 名称 | string | 股票名称 |
| daily_日期 | string | 日K最新日期 |
| daily_收盘 | float | 日K最新收盘价 |
| daily_TD计数 | integer | 日K当前TD计数 |
| daily_9底 | boolean | ✓表示达到9底 |
| daily_8底+ | boolean | ✓表示达到8底及以上 |
| daily_7底+ | boolean | ✓表示达到7底及以上 |
| weekly_* | - | 周K相关字段（同上） |
| monthly_* | - | 月K相关字段（同上） |
| 最大TD计数 | integer | 各周期中的最大TD计数 |