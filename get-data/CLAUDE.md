# get-data L2 Map

[PROTOCOL]: 变更时更新此头部，然后检查根目录 CLAUDE.md

## 模块角色
负责全市场股票基础行情、概念、行业及资金流数据的拉取与入库同步。

## 成员清单
### 核心服务 (L2/services)
- `fetch_daily_history.py`: 历史 K 线补全 (Slow)
- `fetch_daily_snap.py`: 每日行情快照 (Fast)

### 数据抓取器 (L2/fetchers)
- `fetch_concept_sina.py` / `fetch_concept_akshare.py`: 概念数据
- `fetch_industry_baostock.py` / `fetch_industry_akshare.py`: 行业数据
- `fetch_fund_flow.py`: 资金流数据
- `fetch_minute_data.py` / `fetch_minute_akshare.py`: 分时数据

### 工具集 (L2/utils)
- `get_industry_util.py`: 行业工具
- `check_industry.py`: 行业质量检查
- `add_sample_industry.py`: 示例数据填充
- `compare_candidate_pools.py`: 候选池对比

## 暴露接口
- `services.fetch_daily_snap.run_fast_update()`: 全市场快照更新
- `fetchers.fetch_concept_sina.update_csv()`: 概念数据同步到 CSV

## 注意事项
- 优先查 SQLite 数据库，CSV 仅作备份。
- 遵循 8 文件原则，目录已进行 L2 分形分拣。
