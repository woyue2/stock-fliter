# 板块轮动分析与 SQLite 架构迁移计划 (Phase 1)

## 0. 背景与目标
为了支持“从板块到个股”的复盘逻辑及“评论区大哥策略”（板块洗盘博弈反弹），需要在现有 CSV 架构基础上引入 SQLite，解决跨文件关联查询慢、板块聚合计算难、数据存储零碎的问题。

## 1. 核心功能设计
- **板块强度排行 (Sector Strength)**: 每日计算所有概念/行业的平均涨幅、上涨家数比、量比。
- **资金流向监控 (Money Flow)**: 追踪板块近一周的主力资金净流入，识别主力吸筹板块。
- **板块雷电分时 (Sector Intraday)**: 通过合成个股分时，实时生成板块分钟级强度，识别“分时横盘/下跌洗盘”特征。
- **个股对比 (Stock vs Sector)**: 自动对比个股相对于所属板块的强弱，识别“逆势股”和“补涨股”。

## 2. 阶段 1：模块级试验 (当前执行)
保持现有 `get-data` 和 `check-*` 核心逻辑不变，仅在 `analyze-sector-rotation` 模块中引入独立数据库作为试点。

### 2.1 技术实现
- **存储位置**: `analyze-sector-rotation/data/sector_analysis.db`
- **读写逻辑**: 
    1. 从 `get-data/data/selected_stocks_all.csv` 读取元数据。
    2. 从 `get-data/data/fundflow/` 读取个股资金流。
    3. 将上述数据聚合后写入 SQLite。
- **输出**: Markdown/HTML 板块动向日报。

### 2.2 数据库关键表设计
- `stock_metadata`: `code`, `name`, `industry`, `concepts`（基础索引）。
- `sector_stats`: `sector_name`, `date`, `avg_pct`, `total_amount`, `net_inflow_7d`（板块日度统计）。
- `sector_minute_data`: `sector_name`, `datetime`, `strength_index`（高频分时数据）。

## 3. 具体行动路径 (Step-by-Step)
1.  **基础设施**: 创建 `analyze-sector-rotation` 目录及 `db_manager.py`。
2.  **数据灌入**: 编写脚本将 5000 只股票的概念标签和最新日线快照导入数据库。
3.  **板块聚合**: 编写 `calculate_sector_metrics.py`，计算每个板块的整体得分。
4.  **策略对标**: 针对“评论区大哥策略”，专门标记出：**【主力资金周流入前20】+【今日分时在水下震荡】**的板块。
5.  **报告预览**: 输出第一份基于数据库生成的板块复盘分析。

## 4. 后续规划
- **Phase 2**: 抽取 `util/db.py` 为全项目通用数据层，支持 6 个 `data_loader.py` 的透明切换。
- **Phase 3**: 迁移日K线碎文件到数据库，彻底解决 I/O 瓶颈。

---
*Plan Created: 2026-03-05*
*Execution Level: Phase 1 Starting...*
