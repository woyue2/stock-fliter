# -*- coding: utf-8 -*-
"""
报告生成模块
使用与 check-trend-bottom 和 check-steady-uptrend 相同的报告格式和目录结构
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
        
        # 计算最终输出路径
        base_output_dir = Path(__file__).resolve().parent / "output"
        # 按 end_date 归类，格式 YYYY-MM-DD
        if end_date:
            output_dir = base_output_dir / end_date
        else:
            output_dir = base_output_dir / datetime.now().strftime("%Y-%m-%d")
        
        # 再下一层是生成时间，格式 HH-MM-SS
        self.output_dir = output_dir / datetime.now().strftime("%H-%M-%S")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 时间戳用于文件名
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def save_csv(self):
        if self.df.empty:
            return None
            
        filename = f"analysis_result_{self.timestamp}.csv"
        path = self.output_dir / filename
        self.df.to_csv(path, index=False, encoding="utf-8-sig")
        return path
        
    def save_markdown(self):
        if self.df.empty:
            return None
            
        reporter = MarkdownReporter(self.output_dir, self.end_date)
        return reporter.generate(self.df)
        
    def save_html(self):
        if self.df.empty:
            return None
            
        reporter = HTMLReporter(self.output_dir, self.end_date)
        return reporter.generate(self.df)
