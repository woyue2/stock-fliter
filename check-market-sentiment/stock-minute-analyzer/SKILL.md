---
name: stock-minute-analyzer
description: |
  股票分钟级走势形态分析系统。基于240维向量分析，识别股票日内走势形态（单边上涨、V型反转、高开低走等）。
  支持真实分钟数据获取（AkShare API）和日K数据估算两种模式。

  **核心功能：**
  - 单/多股票形态分析
  - 批量市场统计
  - 真实分钟数据获取
  - 早盘vs午盘对比
  - 走势相似度计算

  **触发场景：**
  - "分析XXX股票走势"
  - "批量分析市场情况"
  - "获取分钟数据"
  - "对比多只股票"
---

# Stock Minute Analyzer - 股票分钟形态分析

## 快速开始

```bash
# 进入工作目录
cd ~/Park/stock-fliter

# 分析单只股票（使用真实分钟数据）
python check-market-sentiment/analyze_real_stocks.py --code 600519

# 对比多只股票
python check-market-sentiment/analyze_real_stocks.py --codes 600519,000001,600036

# 批量分析市场
python check-market-sentiment/batch_analyze.py

# 获取分钟数据
python get-data/fetch_minute_akshare.py --code 600519 --realtime
```

## 核心概念

### 240维向量分析

将一天的交易时间（4小时=240分钟）转换为240维向量，捕捉每分钟的走势变化。

```
一天 = 240个采样点 → 240维向量 → 形态识别
```

### 支持的形态类型

| 形态 | 代码 | 特征 |
|------|------|------|
| 单边上涨 | strong_uptrend | 持续走高，收盘高于开盘 |
| 单边下跌 | strong_downtrend | 持续走低，收盘低于开盘 |
| V型反转 | v_reversal | 先跌后涨，午后拉升 |
| 倒V型 | inverted_v | 先涨后跌，午后回落 |
| 高开低走 | high_open_low_close | 开盘冲高后持续走低 |
| 低开高走 | low_open_high_close | 开盘下跌后持续走高 |
| 震荡整理 | consolidation | 波动较大无明显趋势 |
| 平淡走势 | flat | 波动较小方向不明 |

## 工作流程

### 流程1：单股票分析

```
获取分钟数据 → 转换为240维向量 → 提取特征 → 识别形态 → 输出报告
```

**命令：**
```bash
cd ~/Park/stock-fliter
python check-market-sentiment/analyze_real_stocks.py --code 600519
```

**参数：**
| 参数 | 说明 | 示例 |
|------|------|------|
| `--code, -c` | 股票代码 | `--code 600519` |
| `--codes` | 多只股票 | `--codes 600519,000001` |
| `--date, -d` | 指定日期 | `--date 2026-01-30` |

**输出示例：**
```
============================================================
股票代码: 600519
============================================================
✓ 使用真实分钟级数据
分析日期: 2026-02-05 15:00
开盘价: 1524.77
收盘价: 1555.00
分钟数据条数: 238

【形态分析结果】
  形态类型: 低开高走
  日内收益: +1.98%

【早盘 vs 午盘】
  早盘平均: +1.25%
  午盘平均: +1.99%
  → 午盘更强 (+0.74%)
```

### 流程2：批量市场分析

```
遍历所有股票 → 统计形态分布 → 计算市场情绪 → 输出TOP排名
```

**命令：**
```bash
python check-market-sentiment/batch_analyze.py
python check-market-sentiment/batch_analyze.py --sample 100  # 采样100只
python check-market-sentiment/batch_analyze.py --top 20     # TOP20
```

**输出示例：**
```
============================================================
【形态分布统计】
单边上涨    347只 (6.9%)  ███
低开高走   2017只 (40.3%) ████████████████████
高开低走    893只 (17.8%) ████████
单边下跌   1345只 (26.8%) █████████████

【整体市场指标】
平均日内收益: -1.74%
上涨/下跌: 2073/2916 (41.4%/58.2%)

【TOP 10 强势股】
  ✓ 600519  +3.2%  (单边上涨)
  ✓ 000568  +2.8%  (低开高走)
```

### 流程3：获取分钟数据

```
调用AkShare API → 获取实时分钟数据 → 按日期分类存储
```

**命令：**
```bash
cd ~/Park/stock-fliter/get-data

# 单只股票
python fetch_minute_akshare.py --code 600519 --realtime

# 多只股票
python fetch_minute_akshare.py --codes 600519,000001 --realtime

# 全市场采样
python fetch_minute_akshare.py --all --sample 10 --realtime
```

**数据存储结构：**
```
get-data/data/minute_akshare/
├── 2026-02-05/
│   ├── 600519.csv
│   ├── 000001.csv
│   └── 002555.csv
└── 2026-01-26/
    └── ...
```

## 脚本清单

| 脚本 | 路径 | 功能 |
|------|------|------|
| analyze_real_stocks.py | check-market-sentiment/ | 单/多股票分析 |
| batch_analyze.py | check-market-sentiment/ | 批量形态统计 |
| fetch_minute_akshare.py | get-data/ | 获取分钟数据 |
| minute_pattern_analyzer.py | check-market-sentiment/ | 核心分析引擎 |

## 数据来源

### 优先级

1. **AkShare 实时分钟数据** - 最准确，需在线获取
2. **日K数据估算** - 离线可用，精度约80%

### AkShare 配置

```bash
pip install akshare
```

## 故障排除

### 问题1：找不到数据

```bash
# 检查数据目录
ls ~/Park/stock-fliter/get-data/data/minute_akshare/

# 重新获取
cd ~/Park/stock-fliter/get-data
python fetch_minute_akshare.py --code 600519 --realtime
```

### 问题2：分钟数据不足

```bash
# 检查数据条数
python -c "import pandas as pd; df = pd.read_csv('data/minute_akshare/2026-02-05/600519.csv'); print(len(df))"
```

最少需要10条数据才能分析。

### 问题3：分析脚本路径错误

确保在正确目录运行：
```bash
cd ~/Park/stock-fliter/check-market-sentiment
python analyze_real_stocks.py --code 600519
```

## 最佳实践

### 每日复盘流程

```bash
# Step 1: 获取今日分钟数据
cd ~/Park/stock-fliter/get-data
python fetch_minute_akshare.py --codes 600519,000001,600036 --realtime

# Step 2: 分析重点股票
cd ~/Park/stock-fliter/check-market-sentiment
python analyze_real_stocks.py --codes 600519,000001,600036

# Step 3: 查看市场整体
python batch_analyze.py --top 20
```

### 分析结果解读

| 形态 | 信号 | 操作建议 |
|------|------|---------|
| 单边上涨 | 强势 | 持股待涨 |
| V型反转 | 逆转 | 关注延续性 |
| 低开高走 | 午后强 | 资金流入 |
| 高开低走 | 弱势 | 谨慎追高 |
| 平淡走势 | 观望 | 等待方向 |

## 参考资料

- [minute_pattern_analyzer-usage.md](../check-market-sentiment/minute_pattern_analyzer-usage.md) - 详细使用文档
- [minute_pattern_analyzer.py](../check-market-sentiment/minute_pattern_analyzer.py) - 核心分析器源码
