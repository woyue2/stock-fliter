# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  --limit int, --end-date str, --no-open（CLI 参数）
# OUTPUT: None（生成 CSV/MD/HTML 报告，自动打开浏览器）
# POS:    check-volratioxturnxpctchg/main.py
# -*- coding: utf-8 -*-
"""
量比×换手率×涨跌幅 筛选主程序
入口脚本
"""
import sys
import argparse
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

_MOD = Path(__file__).resolve().parent
_ROOT = _MOD.parent
for _p in [str(_MOD), str(_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="量比×换手率×涨跌幅 组合筛选"
    )
    parser.add_argument("--limit", type=int, default=None,
                        help="限制分析股票数量(测试用)")
    parser.add_argument("--end-date", type=str, default=None,
                        help="分析截止日期 (YYYY-MM-DD)")
    parser.add_argument("--no-open", action="store_true",
                        help="不自动打开浏览器")
    parser.add_argument("--config", type=str, default=None,
                        help="JSON 配置路径（默认: config/default.json）")
    args = parser.parse_args()

    run_pipeline(
        limit=args.limit,
        end_date=args.end_date,
        auto_open=not args.no_open,
        config_path=args.config,
    )


if __name__ == "__main__":
    main()
