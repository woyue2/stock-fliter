# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  CLI arguments
# OUTPUT: Return code (int)
# POS:    check-volume-confirmation/main.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pipeline import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(
        description="量价确认筛选（今阳线 + 主力试盘识别）",
    )
    parser.add_argument("--test", action="store_true", help="测试模式，前 10 只股票")
    parser.add_argument("--limit", "-l", type=int, default=None, help="限制扫描股票数量")
    parser.add_argument("--date", "-d", type=str, default=None, help="指定数据日期 (YYYY-MM-DD)")
    parser.add_argument("--no-html", action="store_true", help="不生成 HTML 报告")
    parser.add_argument("--no-markdown", action="store_true", help="不生成 Markdown 报告")
    parser.add_argument("--no-open", action="store_true", help="不自动打开 HTML 报告")
    parser.add_argument("--no-progress", action="store_true", help="关闭扫描进度条显示")
    args = parser.parse_args()

    limit = 10 if args.test and args.limit is None else args.limit

    try:
        result = run_pipeline(
            limit=limit,
            generate_html=not args.no_html,
            generate_markdown=not args.no_markdown,
            auto_open=not args.no_open,
            show_progress=not args.no_progress,
            end_date=args.date,
        )
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        return 1
    except Exception as exc:
        print(f"\n❌ 执行失败: {exc}")
        return 1

    print("\n📊 运行摘要")
    print(f"  扫描股票: {result.get('scanned', 0)}")
    print(f"  命中数量: {result.get('matched', 0)}")
    print(f"  跳过数量: {result.get('skipped', 0)}")

    files = result.get("files", {})
    if files:
        print("\n📁 生成文件")
        for name, path in files.items():
            print(f"  {name}: {path}")

    skip_reasons = result.get("skip_reasons", {})
    if skip_reasons:
        print("\n🧾 跳过原因统计")
        for reason, count in skip_reasons.items():
            print(f"  {reason}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
