# 分钟级市场情绪分析器使用指南

## 目录

- [简介](#简介)
- [快速开始](#快速开始)
- [测试模式](#测试模式)
- [全市场分析](#全市场分析)
- [脚本说明](#脚本说明)
- [输出报告](#输出报告)
- [定时任务](#定时任务)

---

## 简介

基于分钟数据的全市场情绪分析工具，通过分析全市场股票的日内形态分布，推断明日市场走向概率。

### 核心功能

- 📊 全市场分钟数据分析
- 📈 8种形态识别（单边上涨/下跌、V型反转、倒V型、低开高走/高开低走、震荡整理、平淡走势）
- 🔮 明日市场概率推断
- 📑 HTML可视化报告

---

## 快速开始

### 环境要求

```bash
# 创建虚拟环境
conda create -n market_sentiment python=3.12
conda activate market_sentiment

# 安装依赖
pip install akshare pandas numpy
```

### 目录结构

```bash
check-market-sentiment/
├── sentiment_analyzer/     # 核心分析模块
│   ├── data_loader.py      # 数据加载
│   ├── sentiment_engine.py # 情绪计算
│   ├── tomorrow_predictor.py # 明日推断
│   ├── report_generator.py  # 报告生成
│   └── main.py            # 入口脚本
├── fetch_and_analyze.sh    # 自动化脚本
└── output/                # 报告输出目录
```

---

## 测试模式

适用于快速验证功能，使用采样数据。

### 方法1：命令行参数

```bash
cd check-market-sentiment

# 采样100只股票（推荐）
python -m sentiment_analyzer.main --sample 100

# 采样50只股票
python -m sentiment_analyzer.main --sample 50

# 指定日期
python -m sentiment_analyzer.main --date 2026-01-26 --sample 100
```

### 方法2：指定数据目录

```bash
# 指定分钟数据目录
python -m sentiment_analyzer.main \
    --data-dir ~/Park/stock-fliter/get-data/data/minute_akshare \
    --sample 100

# 指定输出目录
python -m sentiment_analyzer.main \
    --sample 100 \
    --output-dir ./reports
```

### 方法3：Python脚本调用

```python
from pathlib import Path
from sentiment_analyzer import (
    DataLoader, SentimentEngine,
    TomorrowPredictor, ReportGenerator
)

# 初始化
data_loader = DataLoader()
engine = SentimentEngine()
predictor = TomorrowPredictor()
generator = ReportGenerator("./output")

# 加载数据
stocks = data_loader.load_all_stocks("2026-01-26", sample=100)

# 分析
patterns = {}  # 需要先做形态分析
stats = engine.aggregate_all(stocks, patterns)
prediction = predictor.predict(stats)

# 生成报告
report_path = generator.generate("2026-01-26", stats, prediction, market_stats)
```

---

## 全市场分析

获取并分析全部A股数据（约5000+股票）。

### 警告

⚠️ **全市场分析需要较长时间**：
- 数据下载：10-30分钟（取决于网络和API限流）
- 形态分析：5-10分钟
- 建议在交易时间运行，或使用 `nohup` 后台运行

### 方法1：自动化脚本（推荐）

```bash
cd check-market-sentiment

# 前台运行（适合测试）
./fetch_and_analyze.sh

# 后台运行（适合生产）
nohup ./fetch_and_analyze.sh > market_full.log 2>&1 &

# 查看进度
tail -f market_full.log
```

### 方法2：分步骤运行

```bash
# Step 1: 获取全市场数据
cd ~/Park/stock-fliter/get-data
python fetch_minute_akshare.py --all --realtime

# Step 2: 分析市场情绪
cd ~/Park/stock-fliter/check-market-sentiment
python -m sentiment_analyzer.main
```

### 查看股票数量

```bash
# 查看已下载的股票数量
ls ~/Park/stock-fliter/get-data/data/minute_akshare/*/*.csv | wc -l
```

---

## 脚本说明

### fetch_and_analyze.sh

自动化脚本，包含数据获取和市场分析。

```bash
# 默认运行
./fetch_and_analyze.sh

# 查看帮助
./fetch_and_analyze.sh --help
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|-----|------|-------|
| `--date, -d` | 分析日期 | 最新可用日期 |
| `--data-dir` | 数据目录 | ~/Park/.../minute_akshare |
| `--output-dir, -o` | 输出目录 | ./output |
| `--sample, -s` | 采样数量 | 无（全部） |
| `--verbose, -v` | 详细输出 | False |

### 输出示例

```
============================================
全市场情绪分析脚本
============================================
目标: 全市场A股 (5000+ 股票)
开始时间: 2026-02-06 00:00:00
============================================

[1/2] 正在获取全市场分钟数据...
开始下载所有A股数据...
数据下载完成，耗时: 1200秒

[2/2] 正在分析全市场情绪...
分析日期: 2026-02-06
分析股票数: 5200
...
============================================
全市场分析完成!
总耗时: 1800秒
报告位置: output/sentiment_2026-02-06.html
============================================
```

---

## 输出报告

### 报告位置

```
output/sentiment_YYYY-MM-DD.html
```

### 报告内容

| 板块 | 说明 |
|-----|------|
| 📊 市场概况 | 平均涨幅、涨跌比、上涨占比 |
| 📈 形态分布 | 8种形态占比饼图 |
| 🔮 明日推断 | 偏强/震荡/偏弱概率 + 置信度 |
| 💡 信号解读 | 推理过程说明 |
| 📉 详细统计 | 早盘/午盘对比、强势股/弱势股 |

### 明日推断示例

```
🔮 明日推断
━━━━━━━━━━━━━━━
  偏强: 45% ↑
  震荡: 30% ─
  偏弱: 25% ↓

  置信度: 50%

💡 信号解读
━━━━━━━━━━
• 低开高走形态占比高于高开低走，显示市场有'抄底'动能
• V型反转较多，午后资金抄底积极
• 综合判断：明日偏强可能性略高
```

---

## 定时任务

### Crontab配置

```bash
# 每天14:30自动运行（交易结束后）
30 14 * * * /home/aa/Park/stock-fliter/check-market-sentiment/fetch_and_analyze.sh >> /var/log/market_sentiment.log 2>&1
```

### Systemd服务（可选）

创建 `/etc/systemd/system/market-sentiment.service`:

```ini
[Unit]
Description=Market Sentiment Analysis
After=network.target

[Service]
Type=oneshot
User=aa
WorkingDirectory=/home/aa/Park/stock-fliter/check-market-sentiment
ExecStart=/bin/bash fetch_and_analyze.sh
StandardOutput=append:/var/log/market_sentiment.log
StandardError=append:/var/log/market_sentiment.err

[Install]
WantedBy=multi-user.target
```

### 启用服务

```bash
# 手动运行
systemctl start market-sentiment

# 查看状态
systemctl status market-sentiment

# 启用开机自启
systemctl enable market-sentiment
```

---

## 常见问题

### Q: 数据下载慢怎么办？

A: 使用采样模式测试：
```bash
python -m sentiment_analyzer.main --sample 100
```

### Q: 报错 "No CSV files found"

A: 检查数据目录：
```bash
ls ~/Park/stock-fliter/get-data/data/minute_akshare/
```

### Q: 如何更新数据？

A: 重新运行脚本：
```bash
./fetch_and_analyze.sh
```

### Q: 报告打开空白？

A: 等待页面加载，或使用Chrome打开：
```bash
google-chrome output/sentiment_*.html
```

---

## 技术细节

### 因子权重

明日推断基于以下因子：

| 因子 | 权重 | 说明 |
|-----|------|------|
| 低开高走 | +0.15 | 抄底动能 |
| 高开低走 | -0.12 | 抛压较重 |
| V型反转 | +0.10 | 午后抄底 |
| 倒V型 | -0.10 | 午后出逃 |
| 午盘强于早盘 | +0.12 | 资金持续流入 |
| 高度一致 | +0.08 | 趋势延续 |

### 置信度

- 样本 < 500: 30%
- 样本 < 1500: 40%
- 样本 < 2500: 50%
- 样本 >= 2500: 55%

---

## 许可证

MIT License
