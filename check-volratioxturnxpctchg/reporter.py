# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  results list and config
# OUTPUT: Paths to generated reports
# POS:    check-volratioxturnxpctchg/reporter.py
# -*- coding: utf-8 -*-
"""
报告生成模块 — 包装 reporters/ 下的 Markdown / HTML 生成器
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

from reporters.markdown_reporter import MarkdownReporter
from reporters.html_reporter import HTMLReporter


class Reporter:

    def __init__(self, results: list, end_date=None):
        self.results = results
        self.df = pd.DataFrame(results)
        self.end_date = end_date

        base = Path(__file__).resolve().parent / "output"
        date_dir = end_date if end_date else datetime.now().strftime("%Y-%m-%d")
        time_dir = datetime.now().strftime("%H-%M-%S")
        self.output_dir = base / date_dir / time_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def save_csv(self):
        if self.df.empty:
            return None
        path = self.output_dir / f"volratio_result_{self.timestamp}.csv"
        self.df.to_csv(path, index=False, encoding="utf-8-sig")
        return path

    def save_markdown(self):
        if self.df.empty:
            return None
        return MarkdownReporter(self.output_dir, self.end_date).generate(self.df)

    def save_html(self):
        if self.df.empty:
            return None
        return HTMLReporter(self.output_dir, self.end_date).generate(self.df)
