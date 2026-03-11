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

### 建议
fetch_daily_snap虽然它很快，但建议你的数据流这样配合  主力更新：每天 15:30 以后跑 

fetch_daily_snap.py，保证数据库里有今天的行情。定期校准：每周五或每月初跑一次 fetch_daily_history.py --all，利用 BaoStock 的专业除权因子把这一周/月里所有除权股票的历史记录重新“刷”一遍，确保数据百分百准确。
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

## 📊 数据源特性 (Platform Data Characteristics)

记录各平台获取的数据特点，以便分析时选择最优数据源：

| 平台 | 获取脚本示例 | 数据特点 | 时效性 | 核心用途 |
| :--- | :--- | :--- | :--- | :--- |
| **Sina (新浪)** | `fetch_daily_snap.py` | 极速全市场快照、题材概念、分时数据 | **实时** (盘中动态更新) | 每日收盘极速入库、实时行情预警 |
| **AkShare** | `fetch_minute_akshare.py` | 整合多方数据、K线、资金流、分钟级精度 | **实时** (部分接口秒级延迟) | 精细化分时分析、各种特色指标获取 |
| **BaoStock** | `fetch_industry_baostock.py` | 申万行业分类、高精度除权历史数据 | **盘后** (通常 16:00 后更新) | 稳定的历史回测、行业基准分类 |
| **Tencent (腾讯)** | `fetch_daily_history.py` | 增量历史K线补齐 | **近实时** (盘中亦可补齐) | 作为历史数据的第二备份源 |

---

## 🧪 功能特性
- **多源冗余**: 整合 Sina、Tencent、BaoStock 等，接口失效时可快速切换。
- **SQLite 核心**: 所有的获取器优先同步到 `data/stocks.db`，实现毫秒级查询。
- **断点续传**: `history` 脚本自动检查 CSV 日期，仅补齐缺失部分。
