# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Chinese A-share stock technical analysis and screening system with multiple strategy modules.

## Common Commands

### Daily Workflow (Full Pipeline)
```bash
# Run everything sequentially
python run_all_strategies.py

# Skip data fetching (use existing data)
python run_all_strategies.py --skip-get-data

# Parallel execution of analysis modules
python run_all_strategies.py --parallel

# Specify end date for backtesting
python run_all_strategies.py --end-date 2026-02-28
```

### Individual Modules

**Data Center (SSOT)**
```bash
cd get-data
python main.py --all              # Full market data fetch
python main.py --test             # Test mode (10 random stocks)
python update_industry.py         # Update industry classification
python fetch_minute_akshare.py --all --realtime  # Real-time minute data
```

**Analysis Modules** (read from `get-data/data/raw/`)
```bash
# TD Bottom Analysis (TD Sequential 9/8/7 bottom signals)
cd check-trend-bottom
python main.py --skip-fetch       # Use local data
python main.py --test --skip-fetch

# Steady Uptrend Analysis (trend following + volatility contraction)
cd check-steady-uptrend
python main.py
python main.py --analyzers 134    # Specific analyzer combo

# Volume Confirmation (yesterday breakout + today bullish)
cd check-volume-confirmation
python main.py --test --no-open
```

**Utilities**
```bash
# Build reports index
python scripts/build_reports_index.py

# Network diagnostics
python diagnose.py

# Compare results between modules
python compare_modules.py
```

## Architecture

### Data Flow
```
get-data/data/raw/*.csv  →  check-*/pipeline.py  →  output/YYYY-MM-DD/HH-MM-SS/
     (Source of Truth)        (Analysis)              (Reports)
```

### Module Structure
Each `check-*` module follows a consistent architecture:

```
check-<strategy>/
├── main.py              # CLI entry point
├── pipeline.py          # Orchestrates: data → analyze → report
├── data_loader.py       # Reads from get-data/data/raw/
├── analyzers/           # Strategy-specific analysis logic
├── reporters/           # HTML/Markdown report generators
└── output/              # Timestamped output directories
```

### Key Shared Components

**util/** - Common utilities used across modules
- `indicators_lib.py` - Technical indicators (RSI, MACD, Bollinger, etc.)
- `progress.py` - Progress bar utilities
- `stream_fetch.py` - Streaming data fetching
- `url_utils.py` - `infer_market_prefix()` / `get_eastmoney_url()` — 东方财富 URL 工具（Phase 5）
- `index_writer.py` - `write_to_stocks_index()` — 索引 CSV 公共写入（Phase 5）
- `minute_analysis/` - Minute-level intraday analysis algorithms (SentimentEngine, TomorrowPredictor, MinutePatternAnalyzer, PatternAnalyzer, DataLoader)

**tools/** - Developer utilities (Phase 2 迁入，不是业务组件)
- `diagnose.py` - 网络/环境诊断工具
- `compare_modules.py` - 模块输出对比工具

**docs/** - 项目文档与演进日志
- `evolution.md` - 技术债 / TODO / 已完成重构的时序记录（由 /git_commit 维护）

**get-data/** - Central data hub
- Outputs to `data/raw/{code}.csv` with columns: date, open, high, low, close, volume, amount, pctChg
- BaoStock primary source, Tencent fallback
- Incremental updates supported

### Strategy Types

| Module | Strategy | Key Metrics |
|--------|----------|-------------|
| check-trend-bottom | TD Sequential | TD9/TD8/TD7 multi-period resonance |
| check-steady-uptrend | Trend following | MA alignment, volatility contraction |
| check-indicator-combo | Indicator combos | 21-strategy combination: TD/MACD/volume/steady (Phase 3 架构对齐) |
| check-volume-confirmation | Volume breakout | Yesterday volume > prior 3 days, today bullish (Phase 6 补全 analyzers/) |
| util/minute_analysis | Intraday pattern algorithms | MinutePatternAnalyzer, SentimentEngine, TomorrowPredictor, PatternAnalyzer, DataLoader (migrated from check-market-sentiment, Phase 0) |


### Output Conventions

All modules output to timestamped directories:
```
output/
├── YYYY-MM-DD/
│   └── HH-MM-SS/
│       ├── *.csv          # Raw data
│       ├── *.html         # Interactive reports
│       └── *.md           # Summary reports
```

Reports are consolidated via `scripts/build_reports_index.py` which generates:
- `reports_list.html` - Master index of all reports
- `reports_index.html` - Searchable/filterable index

### Dependencies

Core: pandas, numpy, requests, tqdm, baostock, akshare

Optional: flask/flask-cors (for api_server.py), gunicorn (deployment)

```bash
pip install -r requirements.txt
```

### Data Format

Stock CSV files (get-data/data/raw/{code}.csv):
- date, code, open, high, low, close, volume, amount, pctChg, tradestatus
- Sorted by date ascending
- Code format: 6-digit (e.g., 000001, 600000)
