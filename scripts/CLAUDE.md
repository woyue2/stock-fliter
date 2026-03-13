# Scripts Module
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

## Overview
This directory contains automation scripts, diagnostic tools, and infrastructure utilities.

## Key Files
- `build_reports_index.py`: Generates the global HTML report index.
- `diagnose.py`: Environment and network diagnostic tool (Migrated from tools/).
- `sync_missing_to_db.py`: CSV 与 SQLite 双向数据一致性同步脚本。

## Usage
Run from project root:
```bash
python scripts/build_reports_index.py
python scripts/diagnose.py
```
