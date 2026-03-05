# SQLite 重构计划 — check-* 全模块

[PROTOCOL]: 变更时更新此头部，然后检查父级 /CLAUDE.md

**目标**：将所有 `check-*` 模块的数据读取从"每次 `pd.read_csv` 开一个文件"改为"统一走 `util/db.py` 读 SQLite"，解决板块聚合查询无法跨文件的根本瓶颈。

---

## 0. 核心设计原则

1. **最小改动面**：只改 `data_loader.py` 中的 `load_daily_data()` 和 `load_selected_stocks()`，所有分析器/报告器**零改动**。
2. **向后兼容**：SQLite 不存在时自动 fallback 到 CSV，保证重构期间各模块可独立运行。
3. **单一数据源**：新建 `util/db.py` 作为唯一数据库接口，6 个 `data_loader.py` 均依赖它，消除重复逻辑。

---

## 1. 将要新建的文件

| 文件 | 职责 |
| :--- | :--- |
| `util/db.py` | SQLite 读写接口（唯一入口） |
| `util/migrate_to_sqlite.py` | 一次性迁移工具：将 5000 个 `raw/*.csv` + `selected_stocks_all.csv` 导入 db |

---

## 2. 将要修改的文件

| 文件 | 修改内容 | 改动量 |
| :--- | :--- | :---: |
| `check-volratioxturnxpctchg/data_loader.py` | `load_daily_data()` 改调 `util/db.py` | 小 |
| `check-td/data_loader.py` | 同上 | 小 |
| `check-tdxmacdxvolume/data_loader.py` | 同上 | 小 |
| `check-maxrsix6u1d/data_loader.py` | 同上 | 小 |
| `check-volupxyangxshipan/data_loader.py` | 同上 | 小 |
| `get-data/main.py` | 写完 CSV 之后额外 upsert 到 SQLite | 小 |
| `/CLAUDE.md` (L1) | 更新架构图，添加 `util/db.py` 说明 | 小 |

---

## 3. 数据库设计 (2 个文件)

### `get-data/data/stocks.db`
```sql
-- 股票元数据表（来源：selected_stocks_all.csv）
CREATE TABLE IF NOT EXISTS stock_info (
    code     TEXT PRIMARY KEY,   -- 6位代码
    name     TEXT NOT NULL,
    bs_code  TEXT NOT NULL,
    industry TEXT DEFAULT '未知',
    concepts TEXT DEFAULT ''
);

-- 日线数据表（来源：raw/*.csv，约 5000只 × 365天）
CREATE TABLE IF NOT EXISTS daily_ohlcv (
    code    TEXT NOT NULL,
    date    TEXT NOT NULL,  -- YYYY-MM-DD
    open    REAL,
    high    REAL,
    low     REAL,
    close   REAL,
    volume  REAL,
    amount  REAL,
    pctchg  REAL,
    turn    REAL,
    PRIMARY KEY (code, date)
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_ohlcv(date);
```

---

## 4. `util/db.py` API 设计

```python
# 核心对外接口（5 个函数，全部 ≤ 20 行）

def get_db_path() -> Path

def get_daily_data(code: str, days: int = 365) -> pd.DataFrame
# 优先走 SQLite，fallback 到 CSV（兼容过渡期）

def get_stock_info_map() -> dict[str, dict]
# 替代各模块中重复的 load_stock_info_map()

def upsert_daily_rows(rows: list[dict]) -> None
# get-data/main.py 写入时调用

def upsert_stock_info(rows: list[dict]) -> None
# fetch_concept_sina.py 等写入元数据时调用
```

---

## 5. 执行顺序 (Phase 2 具体步骤)

### Step 1：创建 `util/db.py` (新文件，不改任何现有逻辑)
### Step 2：创建 `util/migrate_to_sqlite.py` (一次性迁移脚本)
### Step 3：运行迁移，验证数据完整性
### Step 4：逐一改造 5 个 `data_loader.py`（每改一个，立刻运行该模块测试）
### Step 5：改造 `get-data/main.py` 写入端
### Step 6：更新全部 L2/L3 文档，更新 L1 `/CLAUDE.md`

---

## 6. 不动的文件（显式锁定）

以下文件**不在本次重构范围内**，禁止修改：

- `check-*/analyzers/*.py` — 分析逻辑与存储格式无关
- `check-*/reporters/*.py` — 报告生成逻辑不变
- `check-*/pipeline.py` — 流程编排不变
- `check-*/main.py` — CLI 接口不变
- `get-data/fetch_*.py` — 采集脚本不变（除写入端）

---

## 7. 验收标准

每个模块改完后，需通过以下检查：

```bash
# 用测试模式验证输出与改前一致
python check-<module>/main.py --limit 10 --no-open

# 用旧 CSV 做基准对比
# 新旧两次运行结果的命中股票列表必须一致
```

---

*Created: 2026-03-05*
*Status: IN PROGRESS — Phase 2 starting*
