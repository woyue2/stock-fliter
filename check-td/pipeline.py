# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  Pipeline parameters
# OUTPUT: dict (analysis results)
# POS:    check-td/pipeline.py
# -*- coding: utf-8 -*-
"""
TD分析分析流程管理

Pipeline 负责协调各模块：
1. 数据加载 (data_loader)
2. TD分析 (analyzers/td_analyzer)
3. 报告生成 (reporters/html_reporter, markdown_reporter)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import webbrowser

import pandas as pd

from data_loader import OUTPUT_DIR
from analyzers import TDAnalyzer, TDAnalyzerConfig
from reporters import HTMLReporter, MarkdownReporter


@dataclass
class PipelineConfig:
    """Pipeline 配置"""
    # 分析配置
    days: int = 365  # 分析天数
    td_threshold: int = 9  # 九底阈值
    near_threshold: int = 7  # 接近九底阈值
    
    # 输出配置
    output_dir: Path = field(default_factory=lambda: OUTPUT_DIR)
    generate_html: bool = True
    generate_markdown: bool = True
    auto_open_html: bool = True
    
    # 测试配置
    limit: Optional[int] = None  # 限制股票数量
    skip_fetch: bool = False  # 跳过数据获取
    
    # 筛选配置：默认筛选有6底及以上的股票
    filter_levels: list = field(default_factory=lambda: [
        "20+极限", "15-20极地", "10-15深底", "9底", "8底", "7底", "6底"
    ])
    
    end_date: Optional[str] = None  # 截止日期


class Pipeline:
    """TD分析分析 Pipeline"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.data_max_date = None  # 存储数据最新日期

        # 先使用临时目录，等获取到数据最新日期后再确定最终目录
        now = datetime.now()
        temp_date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H-%M-%S")

        # 使用临时目录 output/temp/YYYY-MM-DD/HH-MM-SS
        self.temp_output_dir = self.config.output_dir / "temp" / temp_date_str / time_str
        self.temp_output_dir.mkdir(parents=True, exist_ok=True)

        # 最终的输出目录将在获取数据最新日期后设置
        self.final_output_dir = None
    
    def run(self) -> dict:
        """
        运行完整分析流程
        
        Returns:
            包含分析结果和生成文件路径的字典
        """
        print("\n" + "=" * 60)
        print("🔍 TD分析分析系统")
        print("=" * 60)
        
        result = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "config": {
                "days": self.config.days,
                "td_threshold": self.config.td_threshold,
                "filter_levels": self.config.filter_levels,
            },
            "files": {},
        }
        
        # 1. 运行TD分析
        print("\n📊 第一步: TD分析")
        print("-" * 40)
        
        analyzer_config = TDAnalyzerConfig(
            days=self.config.days,
            td_threshold=self.config.td_threshold,
            near_threshold=self.config.near_threshold,
        )
        analyzer = TDAnalyzer(analyzer_config, self.temp_output_dir)
        df_all, self.data_max_date = analyzer.run(limit=self.config.limit, use_local_files=self.config.skip_fetch)

        if df_all.empty:
            print("  ⚠️ 无分析结果")
            return result

        print(f"  ✅ 分析完成: {len(df_all)} 只股票")
        if self.data_max_date:
            print(f"  📅 数据最新日期: {self.data_max_date.strftime('%Y-%m-%d')}")

        # 确定最终使用的日期
        if self.config.end_date:
            final_date = self.config.end_date
        elif self.data_max_date:
            final_date = self.data_max_date.strftime("%Y-%m-%d")
        else:
            final_date = datetime.now().strftime("%Y-%m-%d")

        # 创建最终输出目录
        time_str = datetime.now().strftime("%H-%M-%S")
        self.final_output_dir = self.config.output_dir / final_date / time_str
        self.final_output_dir.mkdir(parents=True, exist_ok=True)

        # 将临时目录的文件移动到最终目录
        import shutil
        if self.temp_output_dir.exists():
            for item in self.temp_output_dir.glob("*"):
                if item.is_file():
                    shutil.move(str(item), str(self.final_output_dir / item.name))
            # 删除临时目录
            shutil.rmtree(self.temp_output_dir.parent.parent)

        # 保存完整结果
        csv_path = analyzer.save(df_all, output_dir=self.final_output_dir)
        result["files"]["csv"] = str(csv_path)
        print(f"  📄 CSV: {csv_path.name}")
        
        # 统计共振级别
        if "共振级别" in df_all.columns:
            print("\n  📈 底部统计:")
            level_counts = df_all["共振级别"].value_counts()
            for level, count in level_counts.items():
                if count > 0:
                    print(f"      {level}: {count}")
        
        # 2. 筛选符合条件的股票（有7底及以上的）
        print("\n📊 第二步: 筛选")
        print("-" * 40)
        
        if "共振级别" in df_all.columns:
            # 筛选有底部信号的股票（非"无底部信号"）
            df_filtered = df_all[df_all["共振级别"] != "无底部信号"]
            print(f"  ✅ 筛选完成: {len(df_filtered)} 只有底部信号的股票")
        else:
            df_filtered = df_all
            print(f"  ✅ 未设置筛选条件，使用全部 {len(df_filtered)} 只股票")
        
        result["total"] = len(df_all)
        result["filtered"] = len(df_filtered)
        
        # 3. 生成报告
        print("\n📊 第三步: 生成报告")
        print("-" * 40)
        
        if self.config.generate_markdown:
            md_reporter = MarkdownReporter(self.final_output_dir, end_date=self.config.end_date)
            md_path = md_reporter.generate(df_filtered, title="TD分析分析报告")
            result["files"]["markdown"] = str(md_path)
            print(f"  📄 Markdown: {md_path.name}")
        
        if self.config.generate_html:
            # 确定显示日期（优先end_date，否则使用数据最新日期）
            display_date = self.config.end_date or (self.data_max_date.strftime('%Y-%m-%d') if self.data_max_date else None)
            html_reporter = HTMLReporter(self.final_output_dir, end_date=self.config.end_date, display_date=display_date)
            html_path = html_reporter.generate(df_filtered, title="TD分析分析报告")
            result["files"]["html"] = str(html_path)
            print(f"  📄 HTML: {html_path.parent.name}/")
            
            if self.config.auto_open_html:
                print("  🌐 自动打开浏览器...")
                webbrowser.open(html_path.as_uri())
        
        # 完成
        print("\n" + "=" * 60)
        print("✅ 分析完成!")
        print("=" * 60)
        
        return result


def run_pipeline(
    days: int = 365,
    limit: Optional[int] = None,
    generate_html: bool = True,
    generate_markdown: bool = True,
    auto_open: bool = True,
    filter_levels: Optional[list] = None,
    skip_fetch: bool = False,
    end_date: Optional[str] = None,
) -> dict:
    """
    快速运行 Pipeline
    
    Args:
        days: 分析天数
        limit: 限制股票数量（测试用）
        generate_html: 是否生成HTML报告
        generate_markdown: 是否生成Markdown报告
        auto_open: 是否自动打开HTML报告
        filter_levels: 筛选的共振级别列表
        end_date: 截止日期
        
    Returns:
        分析结果字典
    """
    if filter_levels is None:
        filter_levels = ["20+极限", "15-20极地", "10-15深底", "9底", "8底", "7底", "6底"]
    
    config = PipelineConfig(
        days=days,
        limit=limit,
        generate_html=generate_html,
        generate_markdown=generate_markdown,
        auto_open_html=auto_open,
        filter_levels=filter_levels,
        skip_fetch=skip_fetch,
        end_date=end_date,
    )
    
    pipeline = Pipeline(config)
    return pipeline.run()
