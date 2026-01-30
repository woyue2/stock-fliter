# MVP Proposal: Stock Analyzer Platform - Minimum Viable Product

## Executive Summary

A streamlined version of the Stock Analyzer Platform focusing on **core value delivery**: enable users to query historical 9-bottom signals and perform market scans. All non-essential features are deferred to v2.0.

---

## Core Problem Statement

**User Need**: I want to know if a stock had a 9-bottom signal N days ago, and I want to scan the market for stocks with 9-bottom signals.

**Current Pain**:
- Two separate tools (jiudi, others) with no historical data persistence
- Cannot answer: "Was stock X at 9-bottom 3 trading days ago?"
- Must rerun scans to get historical context

**MVP Solution**: A simple tool that:
1. Migrates existing `.pkl` data to SQLite
2. Allows querying historical 9-bottom signals by date
3. Performs market scans on demand

---

## MVP Features

### Must Have (P0 - Core Value)

| # | Feature | Description | RICE Score |
|---|---------|-------------|------------|
| 1 | **TD Sequential Algorithm** | Calculate 9-bottom signals for daily/weekly/monthly | R:5000, I:5, C:0.9, E:8 → 2812 |
| 2 | **Data Migration** | Import ~800 .pkl files to SQLite | R:5000, I:5, C:0.95, E:4 → 5937 |
| 3 | **Historical Query** | Query "was stock X at 9-bottom on date Y?" | R:5000, I:5, C:0.95, E:3 → 7916 |
| 4 | **Market Scan** | Scan all stocks for 9-bottom signals | R:5000, I:4, C:0.95, E:5 → 3800 |
| 5 | **Single-Page UI** | Streamlit app with query and scan functionality | R:5000, I:5, C:0.95, E:6 → 3958 |

### Nice to Have (P1 - Deferred to v2.0)

| # | Feature | Why Deferred | MVP Alternative |
|---|---------|--------------|-----------------|
| 1 | Rate Limiting | Complex to implement, user can control pace | Manual delay between requests |
| 2 | Caching Layer | Compute on demand acceptable for MVP | No caching, compute when needed |
| 3 | Repository Pattern | Overhead for simple app | Direct SQL in services |
| 4 | Multi-Page UI | Navigation complexity | Single page with tabs |
| 5 | Data Validation | Basic checks sufficient | Simple if statements |
| 6 | Type Hints (Strict) | Slows development | Comments only |
| 7 | Comprehensive Specs | Documentation can come later | Basic README only |
| 8 | Pre-commit Hooks | CI/CD not needed for MVP | Manual code review |
| 9 | Trading Calendar Service | akshare provides calendar on demand | Fetch when needed |
| 10 | Error Recovery | Basic error messages sufficient | Print errors to console |

---

## What to Cut

### Cut Completely for MVP

| Component | Original | MVP Version | Time Saved |
|-----------|----------|-------------|------------|
| Rate Limiting Service | 3.8 | Skip entirely | 2 hours |
| Caching Layer | 3.9 | Skip entirely | 2 hours |
| Repository Pattern | 3.7 | Direct SQL | 2 hours |
| Type Hints (Strict) | 3.10 | Optional only | 1 hour |
| Data Validation Spec | specs/data-validation/ | Skip | 1 hour |
| Rate Limiting Spec | specs/rate-limiting/ | Skip | 1 hour |
| Multi-Page UI | 4 pages | 1 page + tabs | 3 hours |
| Language Standards | 500 lines | Basic README | 2 hours |
| Pre-commit Hooks | CI/CD pipeline | Skip | 1 hour |
| Error Recovery | Comprehensive | Basic try/except | 1 hour |

**Total Time Saved: ~16 hours**

---

## MVP Timeline Estimate

| Phase | Task | Time |
|-------|------|------|
| **Phase 1: Setup** | Create project, venv, install deps | 30 min |
| **Phase 2: Core Algorithm** | Port TD Sequential from jiudi_scanner.py | 1 hour |
| **Phase 3: Database** | Simple SQLite schema + migration | 1.5 hours |
| **Phase 4: UI** | Single-page Streamlit app | 2 hours |
| **Phase 5: Testing** | Manual testing + basic asserts | 1 hour |
| | **Total MVP Time** | **~6 hours** |

---

## MVP Tech Stack (Simplified)

| Layer | Full Proposal | MVP Version | Rationale |
|-------|---------------|-------------|-----------|
| Language | Python 3.10+ (strict types) | Python 3.10+ (basic) | Same, less overhead |
| Database | SQLite + Repository Pattern | SQLite (direct SQL) | Simpler, faster to build |
| UI | Multi-page Streamlit | Single-page + tabs | Less navigation complexity |
| Data Source | akshare + caching | akshare only | User controls pace |
| Validation | Pydantic + custom validator | Simple if-checks | MVP doesn't need strict validation |
| Configuration | Pydantic Settings | config.py file | Simpler |

---

## MVP Code Structure

```
stocks-analyzer-mvp/
├── app.py                  # Main Streamlit app (single file)
├── config.py               # Simple configuration
├── database.py             # SQLite helper functions
├── td_sequential.py        # Core TD algorithm
├── scanner.py              # Market scanning logic
├── migrate.py              # One-time .pkl migration
├── requirements.txt        # Minimal dependencies
├── README.md               # Basic documentation
└── data/
    └── stocks.db           # SQLite database
```

### File Descriptions

| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | ~200 | Streamlit UI with tabs (Query/Scan/Settings) |
| `config.py` | ~30 | Constants and configuration |
| `database.py` | ~100 | SQLite connection + CRUD helpers |
| `td_sequential.py` | ~150 | calculate_td_sequence() function |
| `scanner.py` | ~100 | scan_market() function |
| `migrate.py` | ~100 | Import .pkl files to SQLite |
| **Total** | **~680** | **Minimal viable code** |

---

## MVP API / Functions

```python
# database.py
def init_db() -> None:  # Create tables if not exist
def save_prices(stock_code: str, prices: pd.DataFrame) -> None:
def save_td_history(stock_code: str, td_data: dict) -> None:
def get_td_on_date(stock_code: str, date: str, period: str) -> dict:
def get_all_jiudi_on_date(date: str) -> list:
def get_stock_history(stock_code: str, days: int) -> list:

# td_sequential.py
def calculate_td(prices: pd.DataFrame, period: str) -> dict:
    """
    Returns: {
        'td_count': int,      # 0-9
        'is_jiudi': bool,     # True if td_count == 9
        'is_near_jiudi': bool # True if td_count >= 7
    }
    """

# scanner.py
def scan_market(stocks: list, period: str) -> list:
    """Returns list of stocks with is_jiudi=True"""
```

---

## MVP User Interface

```
# Stock Analyzer MVP

[TAB 1: 历史查询] [TAB 2: 市场扫描] [TAB 3: 数据迁移]

### Tab 1: 历史查询
- [股票代码输入框] [查询日期选择器] [查询按钮]
- 结果: 该股票在 [日期] 处于 [日K/周K/月K] [9底/8底/7底/其他]
- 或显示: "该日期无数据"

### Tab 2: 市场扫描
- [扫描范围: 全市场 ▼] [周期: 日K ▼] [开始扫描按钮]
- 进度条: ████░░░░░░░ 40% (320/800)
- 结果表格: 代码 | 名称 | 日K | 周K | 月K | 最新价

### Tab 3: 数据迁移
- [迁移按钮] - 从 .pkl 文件导入数据
- 进度: 已迁移 0/800 只股票
```

---

## MVP Success Criteria

| Criteria | Target | How to Measure |
|----------|--------|----------------|
| Data Migration | 800 stocks migrated | Count in SQLite |
| TD Calculation | Results match jiudi_scanner.py | Spot check 10 stocks |
| Historical Query | Query returns correct 9-bottom status | Manual verification |
| Market Scan | Scan finds expected signals | Compare with legacy tool |
| UI Loads | App launches without error | Streamlit runs successfully |
| Performance | Scan completes in < 5 minutes | Timer measurement |

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Legacy .pkl format changed | High | Low | Test with 1 file before bulk migration |
| akshare API rate limit | Medium | Low | User controls request pace manually |
| SQLite performance | Low | Medium | Add indexes on critical columns |
| Streamlit state issues | Low | Medium | Use session_state carefully |

---

## MVP Success Metrics

1. **Functional**: All 4 core features work (TD calc, migration, query, scan)
2. **Data**: 800+ stocks successfully migrated
3. **Performance**: Market scan completes in < 5 minutes
4. **Quality**: No crashes during normal use
5. **User**: Can answer "Was stock X at 9-bottom N days ago?"

---

## Deferred to v2.0

These features are intentionally out of scope for MVP but planned for future:

| Feature | Priority | Reason |
|---------|----------|--------|
| Rate Limiting | High | User pain is low, complexity high |
| Caching Layer | Medium | Acceptable performance without |
| Repository Pattern | Medium | Refactoring can wait |
| Multi-Page UI | Low | Single page sufficient for MVP |
| Comprehensive Tests | Low | Manual testing OK for MVP |
| Pre-commit Hooks | Low | No CI/CD for MVP |
| Data Validation | Low | Basic checks sufficient |
| Language Standards | Low | Can add later |

---

## Comparison: Full Proposal vs MVP

| Dimension | Full Proposal | MVP |
|-----------|---------------|-----|
| **Time Estimate** | 24 hours | 6 hours |
| **Files** | 30+ files | 7 files |
| **Specs** | 5 documents | 0 (README only) |
| **UI Pages** | 4 pages | 1 page + tabs |
| **Database Tables** | 4 + indexes | 3 basic |
| **Services** | 11 services | 3 core |
| **Code Quality** | Strict (mypy, ruff, black) | Basic (works is enough) |
| **Validation** | Pydantic + custom | Simple if-checks |
| **Caching** | FileCache + lru_cache | None |
| **Rate Limiting** | Token bucket | None (manual) |

---

## Recommendation

**Proceed with MVP scope** because:

1. ✅ **Core value delivered**: Users can query historical 9-bottom signals
2. ✅ **Fast to market**: ~6 hours vs 24 hours (75% reduction)
3. ✅ **Low risk**: Simple code = fewer bugs
4. ✅ **Testable**: Can validate in one session
5. ✅ **Iterative**: v2.0 can add complexity after MVP validated

**MVP validates the concept; v2.0 adds polish and scale.**
