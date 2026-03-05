# get-data
这是一个独立的数据获取模块，负责从网络获取股票数据并统一存储。

## 📜 目录结构 (GEB L2 分形)
本目录遵循 GEB 协议进行物理分拣，超过 8 文件即进行分档。

### 🚀 核心服务 (`services/`)
- `fetch_daily_history.py`: (旧 main.py) 增量更新、按天补齐全量历史数据 (BaoStock / Tencent)。
- `fetch_daily_snap.py`: **推荐**。每日收盘后极速更新全市场快照入库 (Sina)。

### 📡 数据抓取器 (`fetchers/`)
- `fetch_industry_baostock.py`: 获取申万行业分类。
- `fetch_concept_sina.py` / `fetch_concept_akshare.py`: 获取股票概念。
- `fetch_fund_flow.py`: 获取主力资金流向数据。
- `fetch_minute_data.py`: 获取精细化分时 K 线数据。

### 🛠️ 工具集 (`utils/`)
- `check_industry.py`: 统计行业覆盖率。
- `compare_candidate_pools.py`: 对比两次扫描的候选池差异。
- `add_sample_industry.py`: 填充测试用的行业数据。

---

## 🚀 使用方法

### 1. 每日极速更新 (最常用)
收盘后 20 秒内更新全市场数据入 SQLite：
```bash
python services/fetch_daily_snap.py
```

### 2. 补全历史数据
如果缺失多日数据，使用此脚本按只补齐：
```bash
python services/fetch_daily_history.py --all
```

### 3. 更新行业信息
```bash
python fetchers/fetch_industry_baostock.py
```

---

## 🧪 功能特性
- **分布式数据源**: 整合 Sina、Tencent、BaoStock 等多个公开接口。
- **SQLite 同步**: 所有的 fetchers 现在都具备双写能力，优先同步到 SQLite。
- **断点续传**: history 脚本会自动检查每个 CSV 文件的最后日期。
