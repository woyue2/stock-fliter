# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  pd.DataFrame
# OUTPUT: Path to Markdown report
# POS:    check-tdxmacdxvolume/reporters/markdown_reporter.py
# -*- coding: utf-8 -*-
"""
Markdown 报告生成器 - 复用 check-td 的格式
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd


class MarkdownReporter:
    """Markdown 报告生成器"""
    
    # 策略类别定义（分组显示）
    STRATEGY_CATEGORIES = {
        "强买入信号": {
            "完美底部": "TD9 + MACD零轴下金叉 + 放量突破",
            "黄金组合": "TD9 + MACD零轴下金叉",
            "强力买入": "MAxRSIx6U1D + 放量突破"
        },
        "中买入信号": {
            "TD突破": "TD9 + 放量突破",
            "MACD突破": "MACD零轴下金叉 + 放量突破"
        },
        "观察信号": {
            "潜力反转": "非MAxRSIx6U1D + MACD零轴下金叉",
            "TD上升": "TD9 + MAxRSIx6U1D", 
            "MAxRSIx6U1D加MACD": "MAxRSIx6U1D + MACD零轴下金叉",
            "一般持有": "MAxRSIx6U1D + 非放量突破",
            "左侧关注": "TD9 或 MACD零轴下金叉"
        }
    }
    
    def __init__(self, output_dir: Path, end_date: Optional[str] = None):
        self.output_dir = output_dir
        self.end_date = end_date
    
    def generate(
        self,
        df: pd.DataFrame,
        title: str = "新策略分析报告",
        filename: Optional[str] = None,
    ) -> Path:
        """生成 Markdown 报告"""
        if filename is None:
            now = datetime.now()
            ts = now.strftime("%H%M%S")
            date_str = self.end_date if self.end_date else now.strftime("%Y%m%d")
            date_str = date_str.replace("-", "")
            filename = f"new_strategy_report_{date_str}_{ts}.md"
        
        lines = []
        lines.append(f"# {title}\n")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 总览统计
        lines.append("## 策略信号统计\n")
        lines.append(f"- 有信号股票总数: {len(df)}\n")
        
        if "所属策略" in df.columns:
            # 统计各策略的股票数量
            strategy_counts = {}
            # 遍历所有策略类别和子策略
            for category, strategies in self.STRATEGY_CATEGORIES.items():
                lines.append(f"\n### {category}\n")
                for strategy_name in strategies.keys():
                    # 计算包含该策略的股票数量（因为可能有多个策略）
                    count = len(df[df["所属策略"].str.contains(strategy_name, na=False)])
                    strategy_counts[strategy_name] = count
                    lines.append(f"- {strategies[strategy_name]}: {count}\n")
        
        # 板块分布
        lines.append("\n## 板块分布\n")
        if "板块" in df.columns:
            board_stats = df["板块"].value_counts()
            for board, count in board_stats.items():
                pct = count / len(df) * 100
                lines.append(f"- {board}: {count} ({pct:.1f}%)\n")
        
        # 行业分布
        lines.append("\n## 行业分布 (Top 20)\n")
        if "行业" in df.columns:
            industry_stats = df["行业"].value_counts().head(20)
            for industry, count in industry_stats.items():
                pct = count / len(df) * 100
                lines.append(f"- {industry}: {count} ({pct:.1f}%)\n")
        
        # 分类列表（分组显示）
        for category, strategies in self.STRATEGY_CATEGORIES.items():
            lines.append(f"\n## {category}\n")
            
            for strategy_name, strategy_desc in strategies.items():
                sub_df = df[df["所属策略"].str.contains(strategy_name, na=False)] if "所属策略" in df.columns else pd.DataFrame()
                if sub_df.empty:
                    continue
                
                lines.append(f"\n### {strategy_desc} ({len(sub_df)}只)\n")
                lines.append("\n| 代码 | 名称 | 板块 | 行业 | 最新收盘 | 最新日期 | MAxRSIx6U1D | 放量突破 | MACD金叉 | MACD值 | TD计数 | 所属策略 |\n")
                lines.append("|------|------|------|------|----------|----------|----------|----------|---------|--------|--------|----------|\n")
                
                for _, row in sub_df.iterrows():
                    code = row.get("代码", "")
                    name = row.get("名称", "")
                    board = row.get("板块", "")
                    industry = row.get("行业", "")
                    latest_close = row.get("最新收盘", "")
                    latest_date = row.get("最新日期", "")
                    steady_uptrend = "✅" if row.get("MAxRSIx6U1D", False) else ""
                    volume_breakout = "✅" if row.get("放量突破", False) else ""
                    macd_gold = "✅" if row.get("MACD金叉(零下)", False) else ""
                    macd_strength = row.get("MACD值", 0)
                    td_count = row.get("TD计数", 0)
                    strategies_combined = row.get("所属策略", "")
                    
                    lines.append(f"| {code} | {name} | {board} | {industry} | {latest_close} | {latest_date} | {steady_uptrend} | {volume_breakout} | {macd_gold} | {macd_strength} | {td_count} | {strategies_combined} |\n")
        
        # 写入文件
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        return path
