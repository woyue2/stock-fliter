# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  CLI arguments 
# OUTPUT: Return code (int)
# POS:    check-maxrsix6u1d/main.py
# -*- coding: utf-8 -*-
"""
股票筛选主程序 - 重构版

流程：
1. 获取代码 - 从本地数据加载股票列表和日线数据
2. 分析代码 - 运行各种分析器（MAxRSIx6U1D、趋势、网格、6U1D）
3. 生成报告 - 输出 CSV、MD、HTML

使用方法：
  无参数            全量扫描
  --test            测试 10 只
  --random-test     随机测试 50 只
  python main.py --skip-fetch       # 跳过数据获取（使用已有分析结果）
  python main.py --only-report      # 仅生成报告
  python main.py --analyzers 1,3,4  # 指定分析器
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pipeline import Pipeline, PipelineConfig


def parse_args():
    parser = argparse.ArgumentParser(
        description="股票筛选主程序",
        epilog="运行模式（默认全量）: 无参数 全量 | --test 10只 | --random-test 50只",
    )
    parser.add_argument("--test", "-t", action="store_true", help="测试模式，10 只股票")
    parser.add_argument("--random-test", action="store_true", help="随机测试，50 只股票")
    parser.add_argument("--skip-fetch", action="store_true", help="跳过数据获取，使用已有分析结果")
    parser.add_argument("--only-report", action="store_true", help="仅生成报告（需要已有分析结果）")
    parser.add_argument("--analyzers", type=str, default="1,3,4,x",
                        help="指定分析器: 1=MAxRSIx6U1D, 3=趋势分析, 4=网格测试, x=6U1D指标")
    parser.add_argument("--limit", type=int, default=None, help="[高级] 限制扫描股票数量（未传 --test/--random-test 时生效）")
    parser.add_argument("--output-dir", type=str, default=None, help="输出目录")
    parser.add_argument("--grid-horizon", type=int, default=20, help="网格测试收益周期")
    parser.add_argument("--end-date", type=str, default=None, help="分析截止日期 (YYYY-MM-DD)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    
    # 运行模式：--random-test 优先于 --test，否则用 --limit（None=全量）
    if args.random_test:
        limit = 50
    elif args.test:
        limit = 10
    else:
        limit = args.limit
    
    # 解析分析器选项
    analyzer_codes = [a.strip() for a in args.analyzers.split(",") if a.strip()]
    
    config = PipelineConfig(
        use_ma_alignment="1" in analyzer_codes,
        use_trend_analysis="3" in analyzer_codes,
        use_grid_test="4" in analyzer_codes,
        use_6u1d="x" in analyzer_codes,
        grid_horizon=args.grid_horizon,
        limit=limit,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        end_date=args.end_date,
    )
    
    pipeline = Pipeline(config)
    
    if args.only_report:
        # 仅生成报告
        print("[INFO] 仅生成报告模式...")
        return pipeline.generate_reports_only()
    
    if args.skip_fetch:
        # 跳过数据获取，使用已有分析结果
        print("[INFO] 跳过数据获取，使用已有分析结果...")
        return pipeline.run_analysis_and_reports()
    
    # 完整流程
    print("[INFO] 开始完整分析流程...")
    return pipeline.run_full()


if __name__ == "__main__":
    raise SystemExit(main())
