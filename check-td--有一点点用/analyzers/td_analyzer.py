# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  Configuration and limits
# OUTPUT: DataFrame with analysis result
# POS:    check-td/analyzers/td_analyzer.py
# -*- coding: utf-8 -*-
"""
TD多底分析器
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd

util_dir = Path(__file__).resolve().parent.parent.parent / "util"
if str(util_dir) not in sys.path:
    sys.path.append(str(util_dir))

try:
    from progress import ProgressBar
except ImportError:
    class ProgressBar:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def update(self, *args, **kwargs): pass

from data_loader import (
    iter_stock_items, load_daily_data, get_board_type, 
)
from indicators_lib import TechnicalIndicators
from util.td_core import TDCore


@dataclass
class TDAnalyzerConfig:
    days: int = 365
    td_threshold: int = 9
    near_threshold: int = 7
    six_threshold: int = 6
    end_date: Optional[str] = None


from concurrent.futures import ProcessPoolExecutor, as_completed
import os

# 导入系统工具
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))
from util.system_utils import get_optimal_worker_count


def _worker_process_stock_td(item: Any, config: TDAnalyzerConfig) -> Tuple[Optional[Dict], Optional[datetime]]:
    """子进程执行单个股票 TD 分析"""
    try:
        df = load_daily_data(item.code, config.days)
        if df.empty:
            return None, None
            
        # 1. 过滤截止日期
        if config.end_date:
            df["date"] = pd.to_datetime(df["date"])
            df = df[df["date"] <= config.end_date]
            if df.empty:
                return None, None

        last_dt = None
        if "date" in df.columns and not df.empty:
            last_dt = pd.to_datetime(df["date"].iloc[-1])
            
        analyzer = TDAnalyzer(config, Path("."))
        
        analysis = analyzer._analyze_stock(df)
        if "error" in analysis:
            return None, last_dt
            
        analysis.update({
            "代码": item.code,
            "名称": item.name,
            "板块": get_board_type(item.code),
            "行业": getattr(item, "industry", "未知") or "未知"
        })
        
        return analysis, last_dt
    except Exception:
        return None, None


class TDAnalyzer:
    def __init__(self, config: TDAnalyzerConfig, output_dir: Path):
        self.config = config
        self.output_dir = output_dir
    
    def _pre_check_date(self, stocks: list) -> None:
        if not stocks:
            return
        for item in stocks[:3]:
            try:
                df = load_daily_data(item.code, self.config.days)
                if not df.empty and "date" in df.columns:
                    last_dt = pd.to_datetime(df["date"].iloc[-1])
                    print(f"[数据] 分析数据基准日期: {last_dt.strftime('%Y-%m-%d')}")
                    break
            except Exception:
                continue

    def run(self, limit: Optional[int] = None, use_local_files: bool = False, end_date: Optional[str] = None) -> tuple[pd.DataFrame, Optional[datetime]]:
        if end_date:
            self.config.end_date = end_date
            
        stocks = list(iter_stock_items(limit=limit, from_raw=use_local_files))
        print(f"  📈 开始分析 {len(stocks)} 只股票...")
        self._pre_check_date(stocks)

        results = []
        global_max_date = None
        fails = 0
        
        # 计算并行工作进程数
        if os.environ.get("LOW_MEM_MODE") == "1":
            workers = 1
            print("  [INFO] 低内存模式：使用单进程扫描")
        else:
            workers = get_optimal_worker_count()
            if workers > 1:
                print(f"  [INFO] 开启服务器级优化：使用 {workers} 个进程并行扫描")
            else:
                print("  [INFO] 系统资源有限：使用单进程扫描")

        if workers > 1:
            with ProcessPoolExecutor(max_workers=workers) as executor:
                # 提交任务
                future_to_stock = {
                    executor.submit(_worker_process_stock_td, item, self.config): item 
                    for item in stocks
                }
                
                with ProgressBar(len(stocks), desc="并行TD分析") as pbar:
                    for future in as_completed(future_to_stock):
                        try:
                            res, dt = future.result()
                            if dt and (global_max_date is None or dt > global_max_date):
                                global_max_date = dt
                            if res:
                                results.append(res)
                                pbar.update(1, success=True)
                            else:
                                fails += 1
                                pbar.update(1, success=False)
                        except Exception as e:
                            pbar.update(1, success=False)
                            fails += 1
        else:
            # 串行执行
            with ProgressBar(len(stocks), desc="TD分析") as pbar:
                for item in stocks:
                    try:
                        res, dt = self._process_single_stock(item, pbar)
                        if dt and (global_max_date is None or dt > global_max_date):
                            global_max_date = dt
                        if res:
                            results.append(res)
                        else:
                            fails += 1
                    except Exception:
                        pbar.update(1, success=False)
                        fails += 1
                        
        print(f"[统计] 总计: {len(stocks)} | 成功: {len(results)} | 失败: {fails}")
        return self._format_results(results), global_max_date

    def _process_single_stock(self, item: Any, pbar: Any) -> Tuple[Optional[Dict], Optional[datetime]]:
        # 保持此方法用于串行模式
        df = load_daily_data(item.code, self.config.days)
        if df.empty:
            pbar.update(1, success=False)
            return None, None
            
        # 1. 过滤截止日期
        if self.config.end_date:
            df["date"] = pd.to_datetime(df["date"])
            df = df[df["date"] <= self.config.end_date]
            if df.empty:
                pbar.update(1, success=False)
                return None, None

        last_dt = None
        if "date" in df.columns and not df.empty:
            last_dt = pd.to_datetime(df["date"].iloc[-1])
            
        analysis = self._analyze_stock(df)
        if "error" in analysis:
            pbar.update(1, success=False)
            return None, last_dt
            
        analysis.update({
            "代码": item.code,
            "名称": item.name,
            "板块": get_board_type(item.code),
            "行业": getattr(item, "industry", "未知") or "未知"
        })
        
        pbar.update(1, success=True)
        return analysis, last_dt

    def _format_results(self, results: list) -> pd.DataFrame:
        if not results:
            return pd.DataFrame()
        
        result_df = pd.DataFrame(results)
        column_order = [
            "代码", "名称", "板块", "行业",
            "日TD计数", "周TD计数", "月TD计数",
            "共振级别", "底部详情", "波动率", "底部权重", "9底及以上周期数",
            "日底部级别", "周底部级别", "月底部级别",
            "日9底", "日8底", "日7底", "日6底", "周9底", "周8底", "周7底", "周6底",
            "月9底", "月8底", "月7底", "月6底",
            "日最近高底日期", "日最近高底价格", "周最近高底日期", "周最近高底价格",
            "月最近高底日期", "月最近高底价格",
            "日最新日期", "日最新价", "周最新日期", "周最新价", "月最新日期", "月最新价",
            "日最高价", "日最低价", "日均价", "周最高价", "周最低价", "周均价",
            "月最高价", "月最低价", "月均价",
        ]
        return result_df[[c for c in column_order if c in result_df.columns]]

    def _analyze_stock(self, df_daily: pd.DataFrame) -> Dict:
        """调用统一的 TD 核心逻辑"""
        return TDCore.full_analyze(df_daily)

    def save(self, df: pd.DataFrame, filename: Optional[str] = None, output_dir: Optional[Path] = None) -> Path:
        if filename is None:
            if self.config.end_date:
                # 使用 end_date 作为文件名核心
                clean_date = self.config.end_date.replace("-", "")
                ts = datetime.now().strftime("%H%M%S")
                filename = f"td_analysis_{clean_date}_{ts}.csv"
            else:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"td_analysis_{ts}.csv"
        save_dir = output_dir if output_dir else self.output_dir
        path = save_dir / filename
        df.to_csv(path, index=False, encoding="utf-8-sig")
        return path
