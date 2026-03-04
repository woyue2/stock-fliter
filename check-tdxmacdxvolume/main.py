# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  --limit int, --end-date str（CLI 参数）
# OUTPUT: None（生成 CSV/MD/HTML 报告，自动打开浏览器）
# POS:    check-tdxmacdxvolume/main.py（Phase 3 对齐架构）
# -*- coding: utf-8 -*-
"""
新策略分析主程序
入口脚本
"""
import sys
import argparse
import webbrowser
from pathlib import Path

# Force UTF-8 output for Windows to support emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass

# 确保模块根目录和项目根在 sys.path
_MOD = Path(__file__).resolve().parent
_ROOT = _MOD.parent
for _p in [str(_MOD), str(_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from pipeline import run_pipeline

def main():
    parser = argparse.ArgumentParser(description="运行 TDxMACDxVolume 分析")
    parser.add_argument("--limit", type=int, help="限制分析股票数量(测试用)", default=None)
    parser.add_argument("--end-date", type=str, help="分析截止日期 (YYYY-MM-DD)", default=None)
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    run_pipeline(
        limit=args.limit,
        end_date=args.end_date,
        auto_open=not args.no_open
    )

if __name__ == "__main__":
    main()
