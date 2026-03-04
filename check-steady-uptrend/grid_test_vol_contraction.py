# -*- coding: utf-8 -*-
"""
网格测试：vol_contraction_breakout 参数优化（仅本地数据）

参数维度：
- 带宽分位阈值 quantile
- 分位滚动窗口 quantile_window
- 量比阈值 vol_ratio_threshold
- 布林带窗口 bb_window
- 标准差倍数 num_std

输出：
- output/vol_contraction_grid_summary_YYYYMMDD_HHMMSS.csv
- output/vol_contraction_grid_report_YYYYMMDD_HHMMSS.md
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from data_loader import iter_stock_items, load_daily_data, load_selected_stocks

try:
    from tqdm import tqdm
    _HAS_TQDM = True
except Exception:
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


def compute_forward_returns(close: pd.Series, index: int, horizons: List[int]) -> Dict[int, float | None]:
    results: Dict[int, float | None] = {}
    for h in horizons:
        if index + h < len(close):
            base = close.iloc[index]
            future = close.iloc[index + h]
            if base and not pd.isna(base) and not pd.isna(future):
                results[h] = float((future / base) - 1.0)
            else:
                results[h] = None
        else:
            results[h] = None
    return results


@dataclass
class GridConfig:
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


def build_param_grid(config: GridConfig) -> List[Dict[str, float]]:
    combos = []
    for bb_window, num_std, quantile, q_window, vol_thr in product(
        config.bb_windows,
        config.num_stds,
        config.quantiles,
        config.quantile_windows,
        config.vol_ratio_thresholds,
    ):
        combos.append({
            "bb_window": bb_window,
            "num_std": num_std,
            "quantile": quantile,
            "quantile_window": q_window,
            "vol_ratio_threshold": vol_thr,
        })
    return combos


def evaluate_combo(df: pd.DataFrame, combo: Dict[str, float], lookback_days: int, horizons: List[int]) -> Dict[int, float | None] | None:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.reset_index(drop=True)

    last_date = df["date"].iloc[-1]
    cutoff = last_date - pd.Timedelta(days=lookback_days)

    close = df["close"].astype(float)
    vols = df["volume"].astype(float)

    bb = bollinger_bands(close, int(combo["bb_window"]), float(combo["num_std"]))
    bandwidth = bb["bandwidth"]
    vol_ratio = volume_ratio(vols, 20)

    low_vol = bandwidth <= bandwidth.rolling(int(combo["quantile_window"])).quantile(float(combo["quantile"]))
    breakout = close > bb["upper"]
    vol_confirm = vol_ratio >= float(combo["vol_ratio_threshold"])

    signal = low_vol & breakout & vol_confirm
    recent = df[signal & (df["date"] >= cutoff)]
    if recent.empty:
        return None

    last_signal = recent.iloc[-1]
    idx = int(last_signal.name)
    return compute_forward_returns(close, idx, horizons)


def main() -> int:
    parser = argparse.ArgumentParser(description="vol_contraction_breakout 网格测试（本地数据）")
    parser.add_argument("--limit", type=int, default=None, help="限制股票数量")
    parser.add_argument("--lookback", type=int, default=120, help="信号回看天数")
    parser.add_argument("--horizons", type=str, default="5,20,60", help="收益区间，如 5,20,60")
    args = parser.parse_args()

    horizons = [int(h.strip()) for h in args.horizons.split(",") if h.strip()]
    config = GridConfig(lookback_days=args.lookback, horizons=horizons)
    combos = build_param_grid(config)

    summary_rows = []

    total_stocks = len(load_selected_stocks()) if args.limit is None else args.limit
    items = list(iter_stock_items(limit=args.limit))

    for combo in combos:
        returns_by_h = {h: [] for h in horizons}
        if _HAS_TQDM:
            iterator = tqdm(items, total=total_stocks, desc=f"组合 {combo}")
        else:
            iterator = items

        for idx, item in enumerate(iterator, 1):
            df = load_daily_data(item.code)
            if df.empty or len(df) < config.min_bars:
                continue

            returns = evaluate_combo(df, combo, config.lookback_days, horizons)
            if returns is None:
                continue
            for h in horizons:
                if returns.get(h) is not None:
                    returns_by_h[h].append(returns[h])

            if not _HAS_TQDM and (idx % 500 == 0 or idx == total_stocks):
                print(f"{combo} 进度: {idx}/{total_stocks}")

        for h in horizons:
            values = returns_by_h[h]
            if not values:
                summary_rows.append({
                    **combo,
                    "horizon": h,
                    "count": 0,
                    "hit_rate": None,
                    "avg_return": None,
                })
                continue
            values_arr = np.array(values, dtype=float)
            summary_rows.append({
                **combo,
                "horizon": h,
                "count": int(len(values_arr)),
                "hit_rate": float((values_arr > 0).mean()),
                "avg_return": float(values_arr.mean()),
            })

    df_summary = pd.DataFrame(summary_rows)

    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    batch_date = now.strftime("%Y-%m-%d")
    batch_time = now.strftime("%H-%M-%S")
    batch_dir = output_dir / batch_date / batch_time
    batch_dir.mkdir(parents=True, exist_ok=True)

    summary_path = batch_dir / f"vol_contraction_grid_summary_{ts}.csv"
    report_path = batch_dir / f"vol_contraction_grid_report_{ts}.md"

    df_summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    top20 = df_summary.sort_values(by=["horizon", "avg_return"], ascending=[True, False]).groupby("horizon").head(10)
    report_lines = [
        f"# vol_contraction_breakout 网格测试报告 ({ts})",
        "",
        f"- 回看天数: {config.lookback_days}",
        f"- 收益区间: {', '.join(map(str, horizons))}",
        "",
        "## Top 10 组合（按 avg_return）",
        "",
        top20.to_markdown(index=False),
    ]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"[OK] 汇总输出：{summary_path}")
    print(f"[OK] 报告输出：{report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
