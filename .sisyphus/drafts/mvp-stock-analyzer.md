# MVP Stock Analyzer Platform - Draft Proposal

## Core Problem Statement

**User Need**: I want to know if a stock had a 9-bottom signal N days ago, and I want to scan the market for stocks with 9-bottom signals.

**Current Pain**:
- Two separate tools (jiudi, others) with no historical data persistence
- Cannot answer: "Was stock X at 9-bottom 3 trading days ago?"
- Must rerun scans to get historical context

## MVP Features (Must Have)

| # | Feature | Description |
|---|---------|-------------|
| 1 | TD Sequential Algorithm | Calculate 9-bottom signals for daily/weekly/monthly |
| 2 | Data Migration | Import ~800 .pkl files to SQLite |
| 3 | Historical Query | Query "was stock X at 9-bottom on date Y?" |
| 4 | Market Scan | Scan all stocks for 9-bottom signals |
| 5 | Single-Page UI | Streamlit app with query and scan functionality |

## What to Cut (Deferred to v2.0)

| Component | Original | MVP Version | Time Saved |
|-----------|----------|-------------|------------|
| Rate Limiting | 3.8 | Skip entirely | 2 hours |
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

## MVP Timeline Estimate

| Phase | Task | Time |
|-------|------|------|
| Phase 1: Setup | Create project, venv, install deps | 30 min |
| Phase 2: Core Algorithm | Port TD Sequential from jiudi_scanner.py | 1 hour |
| Phase 3: Database | Simple SQLite schema + migration | 1.5 hours |
| Phase 4: UI | Single-page Streamlit app | 2 hours |
| Phase 5: Testing | Manual testing + basic asserts | 1 hour |
| **Total MVP Time** | | **~6 hours** |

## MVP Code Structure

```
stocks-analyzer-mvp/
├── app.py              # Main Streamlit app (single file)
├── config.py           # Simple configuration
├── database.py         # SQLite helper functions
├── td_sequential.py    # Core TD algorithm
├── scanner.py          # Market scanning logic
├── migrate.py          # One-time .pkl migration
├── requirements.txt    # Minimal dependencies
├── README.md           # Basic documentation
└── data/
    └── stocks.db       # SQLite database
```

## MVP Success Criteria

1. ✅ 800 stocks successfully migrated from .pkl
2. ✅ TD calculation results match jiudi_scanner.py
3. ✅ Historical query returns correct 9-bottom status
4. ✅ Market scan finds expected signals
5. ✅ App launches and runs without errors
