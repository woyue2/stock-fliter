# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  pd.DataFrame, output path info
# OUTPUT: Path
# POS:    check-volume-confirmation/reporters/markdown_reporter.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


def generate_markdown_report(
    df: pd.DataFrame,
    output_dir: Path,
    title: str,
    report_date: str,
) -> Path:
    ts = datetime.now().strftime("%H%M%S")
    file_path = output_dir / f"summary_{report_date}_{ts}.md"

    lines = [
        f"# {title}",
        "",
        f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 数据日期: {report_date[:4]}-{report_date[4:6]}-{report_date[6:8]}",
        f"- 命中数量: {len(df)}",
        "",
    ]

    if df.empty:
        lines.append("## 命中结果")
        lines.append("")
        lines.append("无命中股票。")
    else:
        lines.extend(
            [
                "## 命中结果",
                "",
                "| 代码 | 名称 | 今天日期 | 今天开盘 | 今天收盘 | 昨天量 | 前2天量 | 前3天量 | 前4天量 |",
                "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for _, row in df.iterrows():
            lines.append(
                f"| {row['code']} | {row['name']} | {row['date_0']} | {row['open_0']:.3f} | {row['close_0']:.3f} "
                f"| {row['volume_m1']:.0f} | {row['volume_m2']:.0f} | {row['volume_m3']:.0f} | {row['volume_m4']:.0f} |"
            )

    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return file_path
