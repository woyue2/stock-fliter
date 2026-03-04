# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  Configuration and limits
# OUTPUT: DataFrame with analysis result
# POS:    check-trend-bottom/analyzers/td_analyzer.py
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


@dataclass
class TDAnalyzerConfig:
    days: int = 365
    td_threshold: int = 9
    near_threshold: int = 7
    six_threshold: int = 6


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

    def _process_single_stock(self, item: Any, pbar: Any) -> Tuple[Optional[Dict], Optional[datetime]]:
        df = load_daily_data(item.code, self.config.days)
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

    def run(self, limit: Optional[int] = None, use_local_files: bool = False) -> tuple[pd.DataFrame, Optional[datetime]]:
        stocks = list(iter_stock_items(limit=limit, from_raw=use_local_files))
        print(f"  📈 开始分析 {len(stocks)} 只股票...")
        self._pre_check_date(stocks)

        results = []
        global_max_date = None
        fails = 0
        
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
                except Exception as e:
                    if fails == 0:
                        print(f"\n❌ 首次错误 (code={item.code}): {e}")
                    pbar.update(1, success=False)
                    fails += 1
                    
        print(f"[统计] 总计: {len(stocks)} | 成功: {len(results)} | 失败: {fails}")
        return self._format_results(results), global_max_date

    def _format_results(self, results: list) -> pd.DataFrame:
        if not results:
            return pd.DataFrame()
        
        result_df = pd.DataFrame(results)
        column_order = [
            "代码", "名称", "板块", "行业",
            "日TD计数", "周TD计数", "月TD计数",
            "共振级别", "底部详情", "底部权重", "9底及以上周期数",
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
        df_daily = df_daily.copy()
        df_weekly = TechnicalIndicators.resample_ohlcv(df_daily, "W")
        try:
            df_monthly = TechnicalIndicators.resample_ohlcv(df_daily, "ME") 
        except Exception:
            df_monthly = TechnicalIndicators.resample_ohlcv(df_daily, "M")
            
        result = {}
        for df, prefix in [(df_daily, "日"), (df_weekly, "周"), (df_monthly, "月")]:
            result.update(self._analyze_period(df, prefix))
            result.update(self._get_td_info(df, prefix))
            
        result.update(self._build_resonance(
            result["日TD计数"], result["周TD计数"], result["月TD计数"]
        ))
        return result
    
    def _analyze_period(self, df: pd.DataFrame, prefix: str) -> Dict:
        if df.empty:
            return {
                f"{prefix}最新日期": "", f"{prefix}最新价": None,
                f"{prefix}最高价": None, f"{prefix}最低价": None, f"{prefix}均价": None,
            }
        last_row = df.iloc[-1]
        return {
            f"{prefix}最新日期": pd.Timestamp(last_row["date"]).strftime("%Y-%m-%d"),
            f"{prefix}最新价": round(float(last_row["close"]), 2),
            f"{prefix}最高价": round(float(df["high"].max()), 2),
            f"{prefix}最低价": round(float(df["low"].min()), 2),
            f"{prefix}均价": round(float(df["close"].mean()), 2),
        }

    def _get_td_level(self, td_count: int) -> str:
        # 10底以上进公司（分组），6-9底个体户（不分组）
        if td_count >= 20: return f"{td_count}底(20+极限)"
        if td_count >= 15: return f"{td_count}底(15-20极地)"
        if td_count >= 10: return f"{td_count}底(10-15深底)"
        if td_count >= 6: return f"{td_count}底"
        return "无"

    def _get_last_high_td(self, sequence: pd.Series, df: pd.DataFrame) -> Tuple[str, Optional[float]]:
        for idx in range(len(sequence) - 1, -1, -1):
            if sequence.iloc[idx] >= 6:
                row = df.iloc[idx]
                return pd.Timestamp(row["date"]).strftime("%Y-%m-%d"), round(float(row["close"]), 2)
        return "", None

    def _get_td_info(self, df: pd.DataFrame, prefix: str) -> Dict:
        if df.empty or "close" not in df.columns:
            return {
                f"{prefix}TD计数": 0, f"{prefix}9底": False, f"{prefix}8底": False,
                f"{prefix}7底": False, f"{prefix}6底": False, f"{prefix}底部级别": "无",
                f"{prefix}最近高底日期": "", f"{prefix}最近高底价格": None,
            }

        close_series = df["close"].reset_index(drop=True).astype(float)
        sequence = TechnicalIndicators.calculate_td_sequence(close_series)
        td_count = int(sequence.iloc[-1]) if not sequence.empty else 0
        
        last_dt, last_price = self._get_last_high_td(sequence, df)
        
        return {
            f"{prefix}TD计数": td_count,
            f"{prefix}9底": td_count >= 9,
            f"{prefix}8底": td_count >= 8,
            f"{prefix}7底": td_count >= 7,
            f"{prefix}6底": td_count >= 6,
            f"{prefix}底部级别": self._get_td_level(td_count),
            f"{prefix}最近高底日期": last_dt,
            f"{prefix}最近高底价格": last_price,
        }
        
    def _comb(self, label: str, val: int, req_idx: List[int], counts: List[int]) -> Optional[Tuple[str, int]]:
        if all(counts[i] >= val for i in req_idx):
            return (label, val)
        return None

    def _build_combinations(self, c: List[int]) -> List[Tuple[str, int]]:
        combos = []
        # 寻找存在的最高共同值，从最高值递减到6，所有数值都支持组合
        max_val = max(c) if c else 0
        if max_val < 6:
            return []
            
        for val in range(max_val, 5, -1):
            # 所有数字都支持探测多周期共振
            combos.append(self._comb("日周月", val, [0, 1, 2], c))
            combos.append(self._comb("日周", val, [0, 1], c))
            combos.append(self._comb("日月", val, [0, 2], c))
            combos.append(self._comb("周月", val, [1, 2], c))
            combos.append(self._comb("日", val, [0], c))
            combos.append(self._comb("周", val, [1], c))
            combos.append(self._comb("月", val, [2], c))
        
        valid_combos = [cb for cb in combos if cb]
        return valid_combos

    def _build_resonance(self, daily: int, weekly: int, monthly: int) -> Dict:
        combinations = self._build_combinations([daily, weekly, monthly])
        
        # 1. 组/阶优先级: 20+ > 15-20 > 10-15 > 9 > 8 > 7 > 6
        def get_group_rank(val):
            if val >= 20: return 6
            if val >= 15: return 5
            if val >= 10: return 4
            return (val - 6) # (9->3, 8->2, 7->1, 6->0)
        
        # 2. 共振级别优先级: 3周期 > 2周期 > 1周期
        def get_resonance_rank(label):
            return len(label) # "日周月"->3, "日周"->2, "日"->1

        # 最终排序权重
        def get_total_priority(x):
            label, val = x
            # group_rank(10,000) + resonance_rank(1,000) + val(1)
            return get_group_rank(val) * 10000 + get_resonance_rank(label) * 1000 + val

        combinations.sort(key=get_total_priority, reverse=True)
        
        if not combinations:
            return {
                "共振级别": "无底部信号",
                "底部详情": "无",
                "底部权重": 0
            }

        top_label, top_val = combinations[0]
        
        # 分组名称
        group_suffix = ""
        if top_val >= 20: group_suffix = "(20+极限)"
        elif top_val >= 15: group_suffix = "(15-20极地)"
        elif top_val >= 10: group_suffix = "(10-15深底)"
        # 6-9 不加后缀，保持个体户状态
        
        level = f"{top_label}{top_val}底{group_suffix}"
        detail_str = " + ".join(f"{n}{v}" for n, v in combinations[:5]) # 核心信号详情
        
        return {
            "9底及以上周期数": sum(c >= 9 for c in [daily, weekly, monthly]),
            "共振级别": level,
            "底部详情": detail_str,
            "底部权重": get_total_priority(combinations[0])
        }

    def save(self, df: pd.DataFrame, filename: Optional[str] = None, output_dir: Optional[Path] = None) -> Path:
        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"td_analysis_{ts}.csv"
        save_dir = output_dir if output_dir else self.output_dir
        path = save_dir / filename
        df.to_csv(path, index=False, encoding="utf-8-sig")
        return path
