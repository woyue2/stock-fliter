# -*- coding: utf-8 -*-
"""
稳步上升分析器

判断股票是否处于稳定上升趋势：
- 均线多头排列（MA5 > MA10 > MA20 > MA30 > MA60）
- 价格站在所有均线之上
- 60日最大回撤在可控范围内
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from data_loader import iter_stock_items, load_daily_data
from indicators import SteadyUptrendConfig, steady_uptrend_signal

try:
    from tqdm import tqdm
    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False


class SteadyUptrendAnalyzer:
    """稳步上升分析器"""
    
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
        self.config = SteadyUptrendConfig()
    
    def run(self) -> tuple[pd.DataFrame, Optional[datetime]]:
        """运行分析，返回结果DataFrame和数据最新日期"""
        results = []
        global_max_date = None  # 存储所有股票数据中的最新日期
        
        items = list(iter_stock_items(limit=self.limit))
        iterator = tqdm(items, desc="稳步上升分析") if _HAS_TQDM else items
        
        for item in iterator:
            df = load_daily_data(item.code)
            if df.empty:
                continue
            
            # Filter by end_date if provided
            if self.end_date:
                df = df[df["date"] <= self.end_date]
                if df.empty:
                    continue
            
            signal = steady_uptrend_signal(df, self.config)

            # 记录数据最新日期
            latest_date = signal.get("latest_date")
            if latest_date:
                try:
                    latest_dt = pd.Timestamp(latest_date)
                    if global_max_date is None or latest_dt > global_max_date:
                        global_max_date = latest_dt
                except Exception:
                    pass

            row = {
                "code": item.code,
                "name": item.name,
                "latest_date": pd.Timestamp(latest_date).strftime("%Y-%m-%d") if latest_date else "",
                "latest_close": signal.get("latest_close"),
                "steady_uptrend": signal.get("steady_uptrend"),
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

            if not self.only_signal or row["steady_uptrend"]:
                results.append(row)

        result_df = pd.DataFrame(results)

        # 打印数据最新日期
        if global_max_date:
            print(f"[稳步上升] 数据最新日期: {global_max_date.strftime('%Y-%m-%d')}")

        # 保存结果
        if self.output_dir:
            self._save_result(result_df)

        return result_df, global_max_date
    
    def _save_result(self, df: pd.DataFrame):
        """保存分析结果"""
        now = datetime.now()
        name = "steady_uptrend_only" if self.only_signal else "steady_uptrend_all"
        output_path = self.output_dir / f"{name}_{now.strftime('%Y%m%d_%H%M%S')}.csv"
        
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"  [OK] 稳步上升结果: {output_path.name} ({len(df)} 只)")
