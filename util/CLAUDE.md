# Util Module
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

## Overview
Core utility functions for database access, progress tracking, and technical indicator calculations.

## Key Files
- `db.py`: Central SQLite database access layer.
- `progress.py`: Console progress bar utilities.
- `indicators_lib.py`: Technical indicators (MA, EMA, etc.).
- `td_core.py`: TD sequence core logic.
- `system_utils.py`: System-level helper functions.

## Usage
Import from other modules:
```python
from util.db import get_daily_data, upsert_daily_rows
from util.indicators_lib import calculate_ma
```
