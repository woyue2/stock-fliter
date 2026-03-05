# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  pd.DataFrame, output_dir, end_date
# OUTPUT: Path to Markdown report
# POS:    check-volratioxturnxpctchg/reporters/markdown_reporter.py
# -*- coding: utf-8 -*-
"""
Markdown 报告生成器
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd


class MarkdownReporter:
    """量比×换手率×涨跌幅 Markdown 报告"""

    def __init__(self, output_dir: Path, end_date: Optional[str] = None):
        self.output_dir = output_dir
        self.end_date = end_date

    def generate(self, df: pd.DataFrame) -> Path:
        """生成 Markdown 报告"""
        now = datetime.now()
        date_str = (self.end_date or now.strftime("%Y%m%d")).replace("-", "")
        filename = f"volratio_report_{date_str}_{now.strftime('%H%M%S')}.md"

        lines = self._build_header(df, now)
        lines += self._build_summary(df)
        lines += self._build_table(df)

        path = self.output_dir / filename
        path.write_text("".join(lines), encoding="utf-8")
        return path

    # ── 私有方法 ────────────────────────────────
    def _build_header(self, df: pd.DataFrame, now: datetime) -> list[str]:
        return [
            "# 量比×换手率×涨跌幅 筛选报告\n\n",
            f"生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n",
            f"命中数量: **{len(df)}** 只\n\n",
        ]

    def _build_summary(self, df: pd.DataFrame) -> list[str]:
        if df.empty:
            return ["暂无命中股票。\n"]
        lines = ["## 统计概览\n\n"]
        lines.append(f"- 平均量比: {df['量比'].mean():.2f}\n")
        lines.append(f"- 平均涨跌幅: {df['涨跌幅%'].mean():.2f}%\n")
        lines.append(f"- 平均换手率: {df['换手率%'].mean():.2f}%\n\n")

        if "行业" in df.columns:
            lines.append("### 行业分布 (Top 10)\n\n")
            top = df["行业"].value_counts().head(10)
            for ind, cnt in top.items():
                lines.append(f"- {ind}: {cnt}\n")
            lines.append("\n")
        return lines

    def _build_table(self, df: pd.DataFrame) -> list[str]:
        if df.empty:
            return []
        cols = ["代码", "名称", "行业", "最新收盘", "涨跌幅%",
                "量比", "换手率%", "总金额(万)", "最新日期"]
        header = "| " + " | ".join(cols) + " |\n"
        sep = "|" + "|".join(["------"] * len(cols)) + "|\n"

        lines = ["## 命中股票列表\n\n", header, sep]
        df_sorted = df.sort_values("量比", ascending=False)
        for _, row in df_sorted.iterrows():
            vals = [str(row.get(c, "")) for c in cols]
            lines.append("| " + " | ".join(vals) + " |\n")
        return lines
