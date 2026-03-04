# Tests Module
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

## Overview
This directory contains regression tests for the core logic, data fetching and indicators.
As the project evolves, these tests ensure that core algorithms (TD Sequential, steady-uptrend, etc.) remain correct.

## Key Files
- `test_new_indicators_lib.py`: Tests for `util/indicators_lib.py`. 
- `test_diagnosis.py`: Tests for network/env diagnostics.
- `test_fetch_fund_flow.py`: Tests for fund flow data fetching.

## Usage
Run tests from project root:
```bash
python tests/test_new_indicators_lib.py
```
