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
python fetch_daily_history.py --all  # Full market data fetch
python fetch_daily_history.py --test # Test mode (10 random stocks)
python fetch_industry_baostock.py    # Update industry classification
python fetch_minute_akshare.py --all --realtime  # Real-time minute data
```

**Analysis Modules** (read from `get-data/data/raw/`)
```bash
# TD Bottom Analysis (TD Sequential (check-td--有一点点用) 9/8/7 bottom signals)
cd check-td--有一点点用
python main.py --skip-fetch       # Use local data
python main.py --test --skip-fetch

# Steady Uptrend Analysis (trend following + volatility contraction)
cd check-maxrsix6u1d
python main.py
python main.py --analyzers 134    # Specific analyzer combo

# Volume Confirmation (yesterday breakout + today bullish)
cd check-volupxyangxshipan--有用
python main.py --test --no-open
```

**Utilities**
```bash
# Build reports index
python scripts/build_reports_index.py

# Network diagnostics
python scripts/diagnose.py
```

## Architecture

### Data Flow
```
get-data/data/raw/*.csv  →  [util/migrate_to_sqlite.py]  →  get-data/data/stocks.db
                                                                      ↓
                                                           util/db.py (统一读写接口)
                                                                      ↓
                                check-*/pipeline.py  →  output/YYYY-MM-DD/HH-MM-SS/
                                     (Analysis)              (Reports)
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
- `db.py` - **统一 SQLite 读写接口**（所有 check-* 模块通过此读取日线数据，优先 SQLite，fallback CSV）
- `migrate_to_sqlite.py` - 一次性迁移工具（raw/*.csv → stocks.db）
- `indicators_lib.py` - Technical indicators (RSI, MACD, Bollinger, etc.)
- `progress.py` - Progress bar utilities
- `stream_fetch.py` - Streaming data fetching
- `url_utils.py` - `url` logic (Eastmoney/Market prefix)
- `index_writer.py` - Stock index CSV shared logic
- `minute_analysis/` - Intraday pattern algorithms

**scripts/** - Infrastructure, diagnostics and automation
- `build_reports_index.py` - Generates global report index
- `diagnose.py` - Network and environment diagnostics
- Run: `python scripts/{script_name}.py`

**docs/** - 项目文档与演进日志
**server/** - API services
- `api_server.py` - Flask API for stock searching
- Run: `python server/api_server.py`

**valueCellMAx/** - 专业复盘与技术交互系统
- `main.py` - Streamlit 主程序
- `data_provider.py` - SQLite 数据供给
- `notes.json` - 复盘笔记本地存储
- Run: `streamlit run valueCellMAx/main.py`

**tests/** - Core logic validation (regression tests)
- `test_new_indicators_lib.py` - Indicators (TD 13/drawdown, etc.)
- Run: `python tests/test_new_indicators_lib.py`

**get-data/** - Central data hub
- Outputs to `data/raw/{code}.csv` with columns: date, open, high, low, close, volume, amount, pctChg
- BaoStock primary source, Tencent fallback
- Incremental updates supported

### Strategy Types

| Module | Strategy | Key Metrics |
|--------|----------|-------------|
| check-td--有一点点用 | TD Sequential | TD9/TD8/TD7 multi-period resonance |
| check-maxrsix6u1d | MAxRSIx6U1D | MA alignment, RSI filtering, 6U1D momentum |
| check-tdxmacdxvolume | TDxMACDxVolume | 21-strategy combination: TD/MACD/volume/steady |
| check-volupxyangxshipan--有用 | VolUp x Yang x Shipan | Yesterday volume > 3d avg, today bullish |
| check-volratioxturnxpctchg | VolRatio x Turn x PctChg | 量比/换手率/涨跌幅 6条件筛选 |
| check-zhulistrength | Zhuli Strength | 主力强度/散户背离/资金效率（主力与散户博弈） |
| analyze-sector-rotation | Sector Rotation | 板块强度/资金流/分时合成（SQLite驱动） |
| util/minute_analysis | Intraday pattern algorithms | MinutePatternAnalyzer, SentimentEngine |
| to-buy--有用 | Trade Records | 实盘记录与买入建议 |

### Database

`get-data/data/stocks.db` — 统一 SQLite 数据库（gitignore）
- `stock_info` — 股票元数据（code, name, industry, concepts）
- `daily_ohlcv` — 日线数据（≈120万行，PRIMARY KEY(code, date)）


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
