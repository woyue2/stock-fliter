# -*- coding: utf-8 -*-
"""
测试不同的网格参数组合
"""
from dataclasses import dataclass
from itertools import product

import pandas as pd
from data_loader import load_daily_data
from grid_test_vol_contraction import bollinger_bands, volume_ratio


@dataclass
class GridCombo:
    """网格参数组合"""
    bb_window: int
    num_std: float
    quantile: float
    quantile_window: int
    vol_ratio_threshold: float
    horizon: int


def has_vol_contraction_signal(code: str, combo: GridCombo, lookback_days: int, min_bars: int) -> bool:
    """检查是否有波动收缩信号"""
    try:
        df = load_daily_data(code)
        if df.empty or len(df) < min_bars:
            return False

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).reset_index(drop=True)

        close = df["close"].astype(float)
        vols = df["volume"].astype(float)

        bb = bollinger_bands(close, combo.bb_window, combo.num_std)
        bandwidth = bb["bandwidth"]
        vol_ratio = volume_ratio(vols, 20)

        low_vol = bandwidth <= bandwidth.rolling(combo.quantile_window).quantile(combo.quantile)
        breakout = close > bb["upper"]
        vol_confirm = vol_ratio >= combo.vol_ratio_threshold

        signal = low_vol & breakout & vol_confirm
        if not signal.any():
            return False

        last_date = df["date"].iloc[-1]
        cutoff = last_date - pd.Timedelta(days=lookback_days)
        recent = df[signal & (df["date"] >= cutoff)]

        return not recent.empty
    except Exception:
        return False


def test_params(mystic_df, param_set, label):
    """测试参数组合"""
    bb_window, num_std, quantile, quantile_window, vol_ratio_threshold = param_set

    combo = GridCombo(
        bb_window=bb_window,
        num_std=num_std,
        quantile=quantile,
        quantile_window=quantile_window,
        vol_ratio_threshold=vol_ratio_threshold,
        horizon=20
    )

    lookback_days = 120
    min_bars = 120

    count = 0
    for _, row in mystic_df.iterrows():
        code = str(row["代码"])
        if has_vol_contraction_signal(code, combo, lookback_days, min_bars):
            count += 1

    pct = count / len(mystic_df) * 100
    print(f"{label:50s} | {count:4d}/{len(mystic_df):4d} ({pct:5.1f}%)")
    return count


def main():
    # 读取玄学候选股票
    trend_df = pd.read_csv("output/2026-01-23/21-35-49/trend_rules_detail_20260205_213739.csv")

    # 测试6连阳的股票
    mystic_df = trend_df[trend_df["玄学_最近6天连续阳线"] == True]

    print(f"测试股票数：{len(mystic_df)} 只有玄学信号（连续6天阳线）\n")
    print("="*90)
    print(f"{'参数组合':50s} | {'通过数':>11s}")
    print("="*90)

    # 当前默认参数（20天最优）
    print("\n【当前默认参数 - 20天收益周期最优】")
    test_params(mystic_df, (20, 2.0, 0.1, 120, 1.5), "当前参数 (quantile=0.1, vol_ratio=1.5)")

    # 测试不同的quantile和vol_ratio_threshold组合
    print("\n【测试不同的 quantile（波动率分位数）】")
    for q in [0.1, 0.2, 0.3, 0.4, 0.5]:
        test_params(mystic_df, (20, 2.0, q, 120, 1.5), f"quantile={q}")

    print("\n【测试不同的 vol_ratio_threshold（成交量阈值）】")
    for v in [1.0, 1.2, 1.5, 1.8, 2.0]:
        test_params(mystic_df, (20, 2.0, 0.1, 120, v), f"vol_ratio_threshold={v}")

    print("\n【测试不同的 quantile_window（分位数窗口）】")
    for w in [60, 90, 120, 150]:
        test_params(mystic_df, (20, 2.0, 0.1, w, 1.5), f"quantile_window={w}")

    print("\n【测试更宽松的组合】")
    # 放宽参数的组合
    test_params(mystic_df, (20, 2.0, 0.3, 120, 1.2), "宽松1 (q=0.3, vol=1.2)")
    test_params(mystic_df, (20, 2.0, 0.4, 120, 1.0), "宽松2 (q=0.4, vol=1.0)")
    test_params(mystic_df, (20, 2.0, 0.5, 90, 1.0), "宽松3 (q=0.5, vol=1.0, win=90)")

    print("\n" + "="*90)


if __name__ == "__main__":
    main()
