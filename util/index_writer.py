# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  rows: list[dict] — 已构建好的索引行列表；report_date: str — YYYYMMDD格式日期；project_root: Path
# OUTPUT: None（写入 get-data/data/stocks_index/{date}/stocks_index.csv）
# POS:    util/index_writer.py（从各 check-* html_reporter 提升，Phase 5）
# -*- coding: utf-8 -*-
"""
股票索引 CSV 写入工具

将各模块的选股结果追加写入统一的 stocks_index.csv，
供 scripts/build_reports_index.py 构建报告总索引使用。

约束：只依赖标准库和 pandas，绝不 import check-* 模块（防循环依赖）。

CSV Schema:
  代码, 名称, 日期, 模块, 策略级别, 报告路径, 板块, 行业, 生成时间
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import pandas as pd


def get_index_dir(report_date: str, project_root: Optional[Path] = None) -> Path:
    """
    获取索引目录路径（自动创建）

    Args:
        report_date: YYYYMMDD 或 YYYY-MM-DD 格式日期
        project_root: 项目根目录（默认自动推断：此文件 /../..）

    Returns:
        get-data/data/stocks_index/{YYYY-MM-DD}/ 目录路径
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent

    if len(report_date) == 8:
        date_folder = f"{report_date[:4]}-{report_date[4:6]}-{report_date[6:8]}"
    else:
        date_folder = report_date

    index_dir = project_root / "get-data" / "data" / "stocks_index" / date_folder
    index_dir.mkdir(parents=True, exist_ok=True)
    return index_dir


def write_to_stocks_index(
    rows: List[dict],
    report_date: str,
    project_root: Optional[Path] = None,
) -> None:
    """
    将选股结果行写入（追加）stocks_index.csv

    Args:
        rows:         已构建好的行字典列表，每行包含 CSV Schema 中的字段
        report_date:  YYYYMMDD 或 YYYY-MM-DD 格式日期
        project_root: 项目根目录（可选，默认自动推断）

    Example:
        from util.index_writer import write_to_stocks_index
        write_to_stocks_index([
            {"代码": "600519", "名称": "贵州茅台", "日期": "2026-03-04",
             "模块": "TD分析", "策略级别": "日9底", "报告路径": "...",
             "板块": "主板", "行业": "白酒", "生成时间": "2026-03-04 14:00:00"}
        ], report_date="20260304")
    """
    if not rows:
        return

    index_dir = get_index_dir(report_date, project_root)
    index_file = index_dir / "stocks_index.csv"

    index_df = pd.DataFrame(rows)
    if index_file.exists():
        index_df.to_csv(index_file, mode="a", header=False,
                        index=False, encoding="utf-8-sig")
    else:
        index_df.to_csv(index_file, index=False, encoding="utf-8-sig")

    print(f"  [OK] 已导出 {len(rows)} 条记录到索引文件")
