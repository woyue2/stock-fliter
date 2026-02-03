# -*- coding: utf-8 -*-
"""
网格测试分析器

对波动收缩突破参数进行网格搜索优化
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Dict, List, Optional
import os

import numpy as np
import pandas as pd

from data_loader import iter_stock_items, load_daily_data

try:
    from tqdm import tqdm
    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window).mean()


def bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0) -> Dict[str, pd.Series]:
    mid = sma(series, window)
    std = series.rolling(window=window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    bandwidth = (upper - lower) / mid
    return {"mid": mid, "upper": upper, "lower": lower, "bandwidth": bandwidth}


def volume_ratio(volumes: pd.Series, window: int = 20) -> pd.Series:
    return volumes / volumes.rolling(window=window).mean()


@dataclass
class GridConfig:
    """网格测试配置"""
    lookback_days: int = 120
    min_bars: int = 120
    horizons: List[int] = None
    bb_windows: List[int] = None
    num_stds: List[float] = None
    quantiles: List[float] = None
    quantile_windows: List[int] = None
    vol_ratio_thresholds: List[float] = None

    def __post_init__(self):
        if self.horizons is None:
            self.horizons = [5, 20, 60]
        if self.bb_windows is None:
            self.bb_windows = [20]
        if self.num_stds is None:
            self.num_stds = [2.0]
        if self.quantiles is None:
            self.quantiles = [0.1, 0.2, 0.3]
        if self.quantile_windows is None:
            self.quantile_windows = [60, 120]
        if self.vol_ratio_thresholds is None:
            self.vol_ratio_thresholds = [1.2, 1.5, 1.8]


def process_stock_task(code: str, config: GridConfig, param_grid: List[Dict[str, float]], end_date: Optional[str] = None) -> Optional[List[Dict[int, List[float]]]]:
    """处理单只股票的网格测试任务"""
    df = load_daily_data(code)
    
    if df.empty:
        return None

    # Filter by end_date if provided
    if end_date:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df[df["date"] <= end_date]

    if len(df) < config.min_bars:
        return None
    
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).reset_index(drop=True)
    
    close = df["close"].astype(float)
    vols = df["volume"].astype(float)
    
    # 预计算通用指标
    bb_cache = {}
    vr_cache = {}
    
    last_date = df["date"].iloc[-1]
    cutoff = last_date - pd.Timedelta(days=config.lookback_days)
    valid_dates = df["date"] >= cutoff
    
    # 为该股票初始化的结果列表，对应 param_grid 的每个组合
    stock_returns = []
    
    for params in param_grid:
        # 初始化当前参数组合的收益记录
        current_combo_returns = {h: [] for h in config.horizons}
        
        # 1. Bollinger Bands
        bb_key = (params["bb_window"], params["num_std"])
        if bb_key not in bb_cache:
            bb_cache[bb_key] = bollinger_bands(close, params["bb_window"], params["num_std"])
        bb = bb_cache[bb_key]
        
        # 2. Volume Ratio
        if "vr" not in vr_cache:
            vr_cache["vr"] = volume_ratio(vols, 20)
        vol_ratio = vr_cache["vr"]
        
        # 3. Specific Signals
        bandwidth = bb["bandwidth"]
        low_vol = bandwidth <= bandwidth.rolling(params["quantile_window"]).quantile(params["quantile"])
        breakout = close > bb["upper"]
        vol_confirm = vol_ratio >= params["vol_ratio_threshold"]
        
        signal = low_vol & breakout & vol_confirm
        
        # 4. Extract Returns
        signal_indices = df[signal & valid_dates].index.tolist()
        
        for idx in signal_indices:
            for h in config.horizons:
                if idx + h < len(close):
                    base = close.iloc[idx]
                    future = close.iloc[idx + h]
                    if base and not pd.isna(base) and not pd.isna(future):
                        ret = float((future / base) - 1.0)
                        current_combo_returns[h].append(ret)
        
        stock_returns.append(current_combo_returns)
        
    return stock_returns


class GridAnalyzer:
    """网格测试分析器"""
    
    def __init__(
        self,
        limit: Optional[int] = None,
        output_dir: Optional[Path] = None,
        horizon: int = 20,
        config: Optional[GridConfig] = None,
        end_date: Optional[str] = None
    ):
        self.limit = limit
        self.output_dir = output_dir or Path(__file__).resolve().parent.parent / "output"
        self.horizon = horizon
        self.config = config or GridConfig()
        self.end_date = end_date
    
    def run(self) -> tuple[pd.DataFrame, Optional[datetime]]:
        """运行分析，返回结果DataFrame和数据最新日期(云端版一律使用串行，避免多进程卡死)。"""
        # 构建参数网格
        param_grid = self._build_param_grid()

        items = list(iter_stock_items(limit=self.limit))
        iterator = tqdm(items, desc="网格测试") if _HAS_TQDM else items

        grid_returns: list = []
        global_max_date: Optional[datetime] = None  # 存储所有股票数据中的最新日期

        # 云端精简版: 直接使用串行处理，避免多进程在 WSL/容器环境中出现僵死
        for item in iterator:
            try:
                stock_returns = process_stock_task(
                    item.code,
                    self.config,
                    param_grid,
                    self.end_date,
                )
                if stock_returns:
                    grid_returns.append(stock_returns)

                    if not self.end_date:
                        df = load_daily_data(item.code)
                        if not df.empty:
                            df["date"] = pd.to_datetime(df["date"])
                            latest_date = df["date"].max()
                            if global_max_date is None or latest_date > global_max_date:
                                global_max_date = latest_date
            except Exception as e:  # noqa: BLE001
                print(f"  ⚠️ 股票 {item.code} 分析失败: {e}")

        # 汇总所有股票的网格测试结果
        results = []
        if grid_returns:
            # 汇总所有参数组合的结果
            param_count = len(param_grid)
            horizon_count = len(self.config.horizons)

            for p_idx in range(param_count):
                params = param_grid[p_idx]
                for h_idx, h in enumerate(self.config.horizons):
                    # 收集所有股票在该参数组合和时间跨度下的收益
                    all_returns = []
                    for stock_ret in grid_returns:
                        if len(stock_ret) > p_idx:
                            combo_ret = stock_ret[p_idx]
                            if h in combo_ret:
                                all_returns.extend(combo_ret[h])

                    if all_returns:
                        stats = {
                            "count": len(all_returns),
                            "hit_rate": sum(1 for r in all_returns if r > 0) / len(all_returns),
                            "avg_return": np.mean(all_returns),
                            "max_return": max(all_returns),
                            "min_return": min(all_returns),
                        }
                    else:
                        stats = {
                            "count": 0,
                            "hit_rate": None,
                            "avg_return": None,
                            "max_return": None,
                            "min_return": None,
                        }

                    results.append({
                        "bb_window": params["bb_window"],
                        "num_std": params["num_std"],
                        "quantile": params["quantile"],
                        "quantile_window": params["quantile_window"],
                        "vol_ratio_threshold": params["vol_ratio_threshold"],
                        "horizon": h,
                        **stats
                    })

        result_df = pd.DataFrame(results)

        # 打印数据最新日期
        if global_max_date:
            print(f"[网格测试] 数据最新日期: {global_max_date.strftime('%Y-%m-%d')}")

        if self.output_dir:
            self._save_results(result_df)

        return result_df, global_max_date

    
    def _build_param_grid(self) -> List[Dict[str, float]]:
        """构建参数网格"""
        combos = []
        for bb_window, num_std, quantile, q_window, vol_thr in product(
            self.config.bb_windows,
            self.config.num_stds,
            self.config.quantiles,
            self.config.quantile_windows,
            self.config.vol_ratio_thresholds,
        ):
            combos.append({
                "bb_window": bb_window,
                "num_std": num_std,
                "quantile": quantile,
                "quantile_window": q_window,
                "vol_ratio_threshold": vol_thr,
            })
        return combos
    
    def _save_results(self, df: pd.DataFrame):
        """保存测试结果"""
        now = datetime.now()
        ts = now.strftime("%Y%m%d_%H%M%S")
        
        # 汇总结果
        summary_path = self.output_dir / f"vol_contraction_grid_summary_{ts}.csv"
        df.to_csv(summary_path, index=False, encoding="utf-8-sig")
        print(f"  [OK] 网格测试汇总: {summary_path.name} ({len(df)} 组参数)")

        # 无有效结果时仅输出CSV, 跳过报告生成, 避免 KeyError
        if df.empty or "horizon" not in df.columns:
            print("  ⚠️ 网格测试结果为空, 跳过Markdown报告生成")
            return

        # 生成报告
        report_path = self.output_dir / f"vol_contraction_grid_report_{ts}.md"
        self._write_report(df, report_path)
        print(f"  [OK] 网格测试报告: {report_path.name}")
    
    def _write_report(self, df: pd.DataFrame, report_path: Path):
        """生成Markdown报告"""
        lines = [
            "# 网格测试报告",
            "",
            f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- 参数组合数: {len(df)}",
            "",
            "## 最优参数（按平均收益）",
            "",
        ]
        
        for h in self.config.horizons:
            h_df = df[df["horizon"] == h].copy()
            if h_df.empty:
                continue
            
            h_df = h_df[h_df["avg_return"].notna()].sort_values("avg_return", ascending=False)
            if h_df.empty:
                continue
            
            best = h_df.iloc[0]
            lines.extend([
                f"### {h}天收益周期",
                "",
                f"- bb_window: {int(best['bb_window'])}",
                f"- num_std: {best['num_std']}",
                f"- quantile: {best['quantile']}",
                f"- quantile_window: {int(best['quantile_window'])}",
                f"- vol_ratio_threshold: {best['vol_ratio_threshold']}",
                f"- 信号数: {int(best['count'])}",
                f"- 胜率: {best['hit_rate']:.1%}" if best['hit_rate'] else "- 胜率: N/A",
                f"- 平均收益: {best['avg_return']:.2%}" if best['avg_return'] else "- 平均收益: N/A",
                "",
            ])
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
