# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  pd.DataFrame, config
# OUTPUT: Path (MD summary)
# POS:    check-trend-bottom/reporters/markdown_reporter.py
# -*- coding: utf-8 -*-
"""
Markdown 报告生成器 - 动态分组版
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd


class MarkdownReporter:
    """Markdown 报告生成器"""
    
    def __init__(self, output_dir: Path, end_date: Optional[str] = None):
        self.output_dir = output_dir
        self.end_date = end_date
    
    def generate(
        self,
        df: pd.DataFrame,
        title: str = "TD底部分析报告",
        filename: Optional[str] = None,
    ) -> Path:
        """生成 Markdown 报告"""
        if filename is None:
            now = datetime.now()
            ts = now.strftime("%H%M%S")
            date_str = self.end_date if self.end_date else now.strftime("%Y%m%d")
            date_str = date_str.replace("-", "")
            filename = f"td_report_{date_str}_{ts}.md"
        
        # 按权重排序（高阶和高度共振优先）
        if "底部权重" in df.columns:
            df = df.sort_values("底部权重", ascending=False)
        
        lines = []
        lines.append(f"# {title}\n")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 总览统计
        lines.append("## 底部信号统计\n")
        lines.append(f"- 有信号股票总数: {len(df)}\n")
        
        if "共振级别" in df.columns:
            level_counts = df["共振级别"].value_counts()
            # 获取所有唯一的共振级别，并按其在该分阵中的最大权重排序
            unique_levels = df.groupby("共振级别")["底部权重"].max().sort_values(ascending=False).index.tolist()
            
            lines.append("\n### 信号分布\n")
            for level in unique_levels:
                count = level_counts.get(level, 0)
                if count > 0:
                    lines.append(f"- {level}: {count}\n")
        
        # 板块分布
        lines.append("\n## 板块分布\n")
        if "板块" in df.columns:
            board_stats = df["板块"].value_counts()
            for board, count in board_stats.items():
                pct = (count / len(df) * 100) if len(df) > 0 else 0
                lines.append(f"- {board}: {count} ({pct:.1f}%)\n")
        
        # 行业分布
        lines.append("\n## 行业分布 (Top 20)\n")
        if "行业" in df.columns:
            industry_stats = df["行业"].value_counts().head(20)
            for industry, count in industry_stats.items():
                pct = (count / len(df) * 100) if len(df) > 0 else 0
                lines.append(f"- {industry}: {count} ({pct:.1f}%)\n")
        
        # 分类列表 - 动态获取级别
        if "共振级别" in df.columns:
            unique_levels = df.groupby("共振级别")["底部权重"].max().sort_values(ascending=False).index.tolist()
            for level in unique_levels:
                if level == "无底部信号":
                    continue
                sub_df = df[df["共振级别"] == level]
                if sub_df.empty:
                    continue
                
                lines.append(f"\n## {level} ({len(sub_df)}只)\n")
                lines.append("\n| 代码 | 名称 | 板块 | 行业 | 日TD | 周TD | 月TD | 底部详情 |\n")
                lines.append("|------|------|------|------|------|------|------|----------|\n")
                
                for _, row in sub_df.iterrows():
                    code = row.get("代码", "")
                    name = row.get("名称", "")
                    board = row.get("板块", "")
                    industry = row.get("行业", "")
                    daily_td = row.get("日TD计数", 0)
                    weekly_td = row.get("周TD计数", 0)
                    monthly_td = row.get("月TD计数", 0)
                    detail = row.get("底部详情", "")
                    lines.append(f"| {code} | {name} | {board} | {industry} | {daily_td} | {weekly_td} | {monthly_td} | {detail} |\n")
        
        # 写入文件
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        return path
