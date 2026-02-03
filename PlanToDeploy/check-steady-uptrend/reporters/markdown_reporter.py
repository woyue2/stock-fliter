# -*- coding: utf-8 -*-
"""
Markdown报告生成器
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd


class MarkdownReporter:
    """Markdown报告生成器"""
    
    def __init__(self, result: Any, output_dir: Path, end_date: Optional[str] = None):
        self.result = result
        self.output_dir = output_dir
        self.end_date = end_date
    
    def generate(self):
        """生成所有Markdown报告"""
        # 汇总报告已在各分析器和组合器中生成
        # 这里生成总览报告
        self._generate_summary_report()
    
    def _generate_summary_report(self):
        """生成总览报告"""
        now = datetime.now()
        ts = now.strftime("%Y%m%d_%H%M%S")
        
        lines = [
            "# 股票筛选总览报告",
            "",
            f"- 生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- 输出目录: {self.output_dir}",
            "",
        ]
        if self.end_date:
            lines.append(f"- 数据日期: {self.end_date}")
            lines.append("")
        lines.extend([
            "## 分析结果汇总",
            "",
        ])
        
        # 稳步上升
        if self.result.steady_uptrend:
            steady = self.result.steady_uptrend
            lines.extend([
                "### 1. 稳步上升分析",
                "",
                f"- 总数: {steady.summary.get('total', 0)} 只",
                f"- 满足条件: {steady.summary.get('signal_count', 0)} 只",
                "",
            ])
        
        # 趋势分析
        if self.result.trend_analysis:
            trend = self.result.trend_analysis
            lines.extend([
                "### 2. 趋势分析",
                "",
                f"- 总数: {trend.summary.get('total', 0)} 只",
                f"- 趋势跟随信号: {trend.summary.get('trend_follow', 0)} 只",
                f"- 上升回撤信号: {trend.summary.get('pullback', 0)} 只",
                f"- 波动收缩突破信号: {trend.summary.get('vol_breakout', 0)} 只",
                "",
            ])
        
        # 网格测试
        if self.result.grid_test:
            grid = self.result.grid_test
            lines.extend([
                "### 3. 网格测试",
                "",
                f"- 参数组合数: {grid.summary.get('param_combos', 0)}",
                f"- 最优周期: {grid.summary.get('best_horizon', 20)} 天",
                "",
            ])
        
        # 玄学指标
        if self.result.mystic:
            mystic = self.result.mystic
            lines.extend([
                "### 4. 玄学指标",
                "",
                f"- 满足玄学条件: {mystic.summary.get('total', 0)} 只",
                "",
            ])
        
        # 组合筛选结果
        if self.result.combined:
            lines.extend([
                "## 组合筛选结果",
                "",
                "| 组合 | 数量 |",
                "|:-----|-----:|",
            ])
            for name, df in self.result.combined.items():
                lines.append(f"| {name} | {len(df)} |")
            lines.append("")
        
        lines.extend([
            "## 优先级说明",
            "",
            "- [STAR]买入: 6连阳后阴线，立即买入机会",
            "- [STAR]等待: 第6天阳线，等明天回调再买",
            "- 无标记: 其他情况",
            "",
        ])
        
        # 保存
        report_path = self.output_dir / f"summary_report_{ts}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        print(f"  [OK] 总览报告: {report_path.name}")
