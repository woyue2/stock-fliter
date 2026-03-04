# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  Pipeline parameters
# OUTPUT: pipeline result int return
# POS:    check-maxrsix6u1d/pipeline.py
# -*- coding: utf-8 -*-
"""
分析流水线模块

负责协调各分析器的运行顺序和数据传递
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd

from data_loader import iter_stock_items, load_daily_data, StockItem


@dataclass
class PipelineConfig:
    """流水线配置"""
    use_ma_alignment: bool = True
    use_trend_analysis: bool = True
    use_grid_test: bool = True
    use_6u1d: bool = True
    grid_horizon: int = 20
    lookback_days: int = 120
    min_bars: int = 120
    limit: Optional[int] = None
    output_dir: Optional[Path] = None
    end_date: Optional[str] = None
    auto_open: bool = True

    def __post_init__(self):
        if self.output_dir is None:
            self.output_dir = Path(__file__).resolve().parent / "output"


@dataclass
class AnalysisResult:
    """单个分析器的结果"""
    name: str
    data: pd.DataFrame
    summary: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


@dataclass
class PipelineResult:
    """流水线整体结果"""
    ma_alignment: Optional[AnalysisResult] = None
    trend_analysis: Optional[AnalysisResult] = None
    grid_test: Optional[AnalysisResult] = None
    pattern_6u1d: Optional[AnalysisResult] = None
    combined: Optional[pd.DataFrame] = None
    batch_dir: Optional[Path] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


class Pipeline:
    """分析流水线"""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.data_max_date = None  # 存储数据最新日期
        self.config = config
        self.result = PipelineResult()
        self._setup_batch_dir()
    
    def _setup_batch_dir(self):
        """创建批次输出目录"""
        now = datetime.now()
        # 优先使用 end_date，否则使用当前日期
        date_str = self.config.end_date if self.config.end_date else now.strftime("%Y-%m-%d")
        batch_time = now.strftime("%H-%M-%S")
        
        # 存放的文件夹也更改为 end-date 的文件夹
        self.result.batch_dir = self.config.output_dir / date_str / batch_time
        self.result.batch_dir.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] 输出目录: {self.result.batch_dir}")
    
    def run_full(self) -> int:
        """运行完整流程：获取数据 -> 分析 -> 生成报告"""
        try:
            self._run_analyzers()
            self._combine_results()
            self._generate_reports()
            print("[OK] 完整流程执行完成")
            return 0
        except Exception as e:
            print(f"[ERROR] 流程执行失败: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    def run_analysis_and_reports(self) -> int:
        """使用已有分析结果，重新组合并生成报告"""
        try:
            self._load_existing_results()
            self._combine_results()
            self._generate_reports()
            print("[OK] 分析和报告生成完成")
            return 0
        except Exception as e:
            print(f"[ERROR] 执行失败: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    def generate_reports_only(self) -> int:
        """仅生成报告（需要已有组合结果）"""
        try:
            self._load_existing_results()
            self._generate_reports()
            print("[OK] 报告生成完成")
            return 0
        except Exception as e:
            print(f"[ERROR] 报告生成失败: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    def _run_analyzers(self):
        """运行各分析器"""
        # 1. MA排列分析 (MA Alignment)
        if self.config.use_ma_alignment:
            print("\n[1/4] 运行 MA 排列分析...")
            self.result.ma_alignment = self._run_ma_alignment()
        
        # 2. 趋势分析（包含6U1D指标）
        if self.config.use_trend_analysis or self.config.use_6u1d:
            print("\n[2/4] 运行趋势分析...")
            self.result.trend_analysis = self._run_trend_analysis()
        
        # 3. 网格测试 (VCP型突破参数)
        if self.config.use_grid_test:
            print("\n[3/4] 运行网格测试...")
            self.result.grid_test = self._run_grid_test()
        
        # 4. 6U1D指标提取 (Momentum)
        if self.config.use_6u1d:
            print("\n[4/4] 提取 6U1D 指标...")
            self.result.pattern_6u1d = self._extract_6u1d_from_trend()
    
    def _run_ma_alignment(self) -> AnalysisResult:
        """运行 MA 排列分析 (原 Steady Uptrend)"""
        from analyzers.ma_alignment_analyzer import MAAlignmentAnalyzer
        
        analyzer = MAAlignmentAnalyzer(
            limit=self.config.limit,
            output_dir=self.result.batch_dir,
            end_date=self.config.end_date
        )
        df, max_date = analyzer.run()

        # 更新全局数据最新日期
        if max_date and (self.data_max_date is None or max_date > self.data_max_date):
            self.data_max_date = max_date

        return AnalysisResult(
            name="ma_alignment",
            data=df,
            summary={
                "total": len(df),
                "signal_count": df["steady_uptrend"].sum() if "steady_uptrend" in df.columns else 0
            }
        )
    
    def _run_trend_analysis(self) -> AnalysisResult:
        """运行趋势分析"""
        from analyzers.trend_analyzer import TrendAnalyzer

        analyzer = TrendAnalyzer(
            limit=self.config.limit,
            output_dir=self.result.batch_dir,
            end_date=self.config.end_date
        )
        df, max_date = analyzer.run()

        # 更新全局数据最新日期
        if max_date and (self.data_max_date is None or max_date > self.data_max_date):
            self.data_max_date = max_date

        return AnalysisResult(
            name="trend_analysis",
            data=df,
            summary={
                "total": len(df),
                "trend_follow": df["趋势跟随_是否信号"].sum() if "趋势跟随_是否信号" in df.columns else 0,
                "pullback": df["上升回撤_是否信号"].sum() if "上升回撤_是否信号" in df.columns else 0,
                "vol_breakout": df["波动收缩突破_是否信号"].sum() if "波动收缩突破_是否信号" in df.columns else 0,
            }
        )

    def _run_grid_test(self) -> AnalysisResult:
        """运行网格测试"""
        from analyzers.grid_analyzer import GridAnalyzer

        analyzer = GridAnalyzer(
            limit=self.config.limit,
            output_dir=self.result.batch_dir,
            horizon=self.config.grid_horizon,
            end_date=self.config.end_date
        )
        df, max_date = analyzer.run()

        # 更新全局数据最新日期
        if max_date and (self.data_max_date is None or max_date > self.data_max_date):
            self.data_max_date = max_date

        return AnalysisResult(
            name="grid_test",
            data=df,
            summary={
                "param_combos": len(df),
                "best_horizon": self.config.grid_horizon
            }
        )

    def _extract_6u1d_from_trend(self) -> AnalysisResult:
        """从趋势分析结果中提取6U1D指标"""
        if self.result.trend_analysis is None:
            return None
        
        df = self.result.trend_analysis.data.copy()
        mystic_cols = [c for c in df.columns if c.startswith("6U1D_")]
        
        if not mystic_cols:
            return None
        
        # 筛选满足任一6U1D条件的股票
        mystic_mask = df[mystic_cols].any(axis=1)
        mystic_df = df[mystic_mask].copy()
        
        return AnalysisResult(
            name="pattern_6u1d",
            data=mystic_df,
            summary={
                "total": len(mystic_df),
                "cols": mystic_cols
            }
        )
    
    def _load_existing_results(self):
        """加载已有的分析结果"""
        from utils import find_latest_file
        
        output_dir = self.config.output_dir
        
        # 加载 MA 排列结果
        if self.config.use_ma_alignment:
            steady_path = find_latest_file(output_dir, "steady_uptrend_*.csv")
            if steady_path:
                df = pd.read_csv(steady_path, encoding="utf-8-sig")
                self.result.ma_alignment = AnalysisResult(
                    name="ma_alignment",
                    data=df,
                    summary={"total": len(df), "source": str(steady_path)}
                )
                print(f"  [OK] 加载 MA 排列: {steady_path.name}")
        
        # 加载趋势分析结果
        if self.config.use_trend_analysis:
            trend_path = find_latest_file(output_dir, "trend_rules_detail_*.csv")
            if trend_path:
                df = pd.read_csv(trend_path, encoding="utf-8-sig")
                self.result.trend_analysis = AnalysisResult(
                    name="trend_analysis",
                    data=df,
                    summary={"total": len(df), "source": str(trend_path)}
                )
                print(f"  [OK] 加载趋势分析: {trend_path.name}")
        
        # 加载网格测试结果
        if self.config.use_grid_test:
            grid_path = find_latest_file(output_dir, "vol_contraction_grid_summary_*.csv")
            if grid_path:
                df = pd.read_csv(grid_path, encoding="utf-8-sig")
                self.result.grid_test = AnalysisResult(
                    name="grid_test",
                    data=df,
                    summary={"total": len(df), "source": str(grid_path)}
                )
                print(f"  [OK] 加载网格测试: {grid_path.name}")
    
    def _combine_results(self):
        """组合各分析结果"""
        from combiners.momentum_combiner import MomentumCombiner
        
        combiner = MomentumCombiner(
            trend_result=self.result.trend_analysis,
            steady_result=self.result.ma_alignment,
            grid_result=self.result.grid_test,
            config=self.config,
            output_dir=self.result.batch_dir
        )
        
        self.result.combined = combiner.run()
    
    def _generate_reports(self):
        """生成报告（MD和HTML）"""
        from reporters.markdown_reporter import MarkdownReporter
        from reporters.html_reporter import HtmlReporter

        # 确定显示日期（优先end_date，否则使用数据最新日期）
        display_date = self.config.end_date or (self.data_max_date.strftime('%Y-%m-%d') if self.data_max_date else None)

        # Markdown报告
        md_reporter = MarkdownReporter(
            result=self.result,
            output_dir=self.result.batch_dir,
            end_date=self.config.end_date
        )
        md_reporter.generate()

        # HTML报告
        html_reporter = HtmlReporter(
            result=self.result,
            output_dir=self.result.batch_dir,
            end_date=self.config.end_date,
            display_date=display_date,
            auto_open=self.config.auto_open
        )
        html_reporter.generate()
