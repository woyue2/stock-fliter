# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  Limit, End Date, Output Dir
# OUTPUT: pd.DataFrame with signal results
# POS:    check-maxrsix6u1d/analyzers/ma_alignment_analyzer.py
# -*- coding: utf-8 -*-
"""
MA排列分析器

判断股票是否处于稳定上升趋势：
- 均线多头排列（MA5 > MA10 > MA20 > MA30 > MA60）
- 价格站在所有均线之上
- 60日最大回撤在可控范围内
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import os
import pandas as pd

from data_loader import iter_stock_items, load_daily_data, StockItem
from indicators import MAAlignmentConfig, ma_alignment_signal

try:
    from tqdm import tqdm
    _HAS_TQDM = os.environ.get("DISABLE_TQDM") != "1"
except ImportError:
    _HAS_TQDM = False


from concurrent.futures import ProcessPoolExecutor, as_completed
import sys

# 导入分析相关函数
from indicators import MAAlignmentConfig, ma_alignment_signal


def _worker_ma_alignment_task(item: any, end_date: Optional[str]) -> Tuple[Optional[Dict], Optional[datetime]]:
    """子进程执行单个股票 MA 排列分析"""
    try:
        df = load_daily_data(item.code)
        if df.empty:
            return None, None

        # Filter by end_date if provided
        if end_date:
            df["date"] = pd.to_datetime(df["date"])
            df = df[df["date"] <= end_date]
            if df.empty:
                return None, None
        
        config = MAAlignmentConfig()
        signal = ma_alignment_signal(df, config)

        # 记录数据最新日期
        latest_date = signal.get("latest_date")
        latest_dt = None
        if latest_date:
            try:
                latest_dt = pd.Timestamp(latest_date)
            except Exception:
                pass

        row = {
            "code": item.code,
            "name": item.name,
            "latest_date": pd.Timestamp(latest_date).strftime("%Y-%m-%d") if latest_date else "",
            "latest_close": signal.get("latest_close"),
            "ma_alignment": signal.get("ma_alignment"),
            "ma5": signal.get("ma5"),
            "ma10": signal.get("ma10"),
            "ma20": signal.get("ma20"),
            "ma30": signal.get("ma30"),
            "ma60": signal.get("ma60"),
            "slope20": signal.get("slope20"),
            "slope30": signal.get("slope30"),
            "slope60": signal.get("slope60"),
            "drawdown_60": signal.get("drawdown_60"),
            "order_ok": signal.get("order_ok"),
            "price_above": signal.get("price_above"),
            "drawdown_ok": signal.get("drawdown_ok"),
        }
        
        return row, latest_dt
    except Exception:
        return None, None


# 导入系统工具
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))
from util.system_utils import get_optimal_worker_count


class MAAlignmentAnalyzer:
    """MA排列分析器"""
    
    def __init__(
        self,
        limit: Optional[int] = None,
        output_dir: Optional[Path] = None,
        only_signal: bool = True,
        end_date: Optional[str] = None
    ):
        self.limit = limit
        self.output_dir = output_dir or Path(__file__).resolve().parent.parent / "output"
        self.only_signal = only_signal
        self.end_date = end_date
        self.config = MAAlignmentConfig()
    
    def run(self) -> tuple[pd.DataFrame, Optional[datetime]]:
        """运行分析，返回结果DataFrame和数据最新日期"""
        results = []
        global_max_date = None  # 存储所有股票数据中的最新日期
        
        items = list(iter_stock_items(limit=self.limit))
        
        # 计算并行工作进程数
        if os.environ.get("LOW_MEM_MODE") == "1":
            workers = 1
            print("  [INFO] 低内存模式：使用单进程扫描")
        else:
            workers = get_optimal_worker_count()
            if workers > 1:
                print(f"  [INFO] 开启服务器级优化：使用 {workers} 个进程运行 MA 排列分析")
            else:
                print("  [INFO] 系统资源有限：使用单进程运行 MA 排列分析")

        if workers > 1:
            with ProcessPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(_worker_ma_alignment_task, item, self.end_date): item 
                    for item in items
                }
                
                iterator = tqdm(as_completed(futures), total=len(items), desc="并行MA排列分析") if _HAS_TQDM else as_completed(futures)
                for future in iterator:
                    res, dt = future.result()
                    if dt and (global_max_date is None or dt > global_max_date):
                        global_max_date = dt
                    if res:
                        if not self.only_signal or res["ma_alignment"]:
                            results.append(res)
        else:
            iterator = tqdm(items, desc="MA排列分析") if _HAS_TQDM else items
            for item in iterator:
                res, dt = _worker_ma_alignment_task(item, self.end_date)
                if dt and (global_max_date is None or dt > global_max_date):
                    global_max_date = dt
                if res:
                    if not self.only_signal or res["ma_alignment"]:
                        results.append(res)

        result_df = pd.DataFrame(results)

        # 打印数据最新日期
        if global_max_date:
            print(f"[MA排列] 数据最新日期: {global_max_date.strftime('%Y-%m-%d')}")

        # 保存结果
        if self.output_dir:
            self._save_result(result_df)

        return result_df, global_max_date
    
    def _save_result(self, df: pd.DataFrame):
        """保存分析结果"""
        now = datetime.now()
        name = "ma_alignment_only" if self.only_signal else "ma_alignment_all"
        output_path = self.output_dir / f"{name}_{now.strftime('%Y%m%d_%H%M%S')}.csv"
        
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"  [OK] MA排列结果: {output_path.name} ({len(df)} 只)")
