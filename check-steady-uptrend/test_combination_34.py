# -*- coding: utf-8 -*-
"""
测试组合34在不同参数下的结果
"""
from dataclasses import dataclass

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


def test_combination_34(param_combo, label):
    """测试组合34的结果"""
    combo = GridCombo(
        bb_window=param_combo[0],
        num_std=param_combo[1],
        quantile=param_combo[2],
        quantile_window=param_combo[3],
        vol_ratio_threshold=param_combo[4],
        horizon=20
    )

    lookback_days = 120
    min_bars = 120

    # 读取趋势分析结果
    trend_df = pd.read_csv("output/2026-01-23/21-35-49/trend_rules_detail_20260205_213739.csv")

    # 组合34 = 趋势分析 + 网格测试
    # 先筛选趋势分析的信号
    trend_mask = (
        trend_df.get("趋势跟随_是否信号", False)
        | trend_df.get("上升回撤_是否信号", False)
        | trend_df.get("波动收缩突破_是否信号", False)
    )
    trend_candidates = trend_df[trend_mask].copy()

    print(f"\n{label}")
    print(f"  参数: bb_window={combo.bb_window}, num_std={combo.num_std}, "
          f"quantile={combo.quantile}, quantile_window={combo.quantile_window}, "
          f"vol_ratio={combo.vol_ratio_threshold}")
    print(f"  趋势分析候选: {len(trend_candidates)} 只")

    # 再筛选网格测试信号
    count_6up = 0
    count_6up1down = 0

    for _, row in trend_candidates.iterrows():
        code = str(row["代码"])

        has_grid = has_vol_contraction_signal(code, combo, lookback_days, min_bars)

        if not has_grid:
            continue

        # 检查玄学条件
        if row.get("玄学_最近6天连续阳线", False):
            count_6up += 1
        if row.get("玄学_10天内有6连阳后1阴", False):
            count_6up1down += 1

    print(f"  组合34 + 6连阳: {count_6up} 只")
    print(f"  组合34 + 近10天6涨1跌: {count_6up1down} 只")

    return count_6up, count_6up1down


def main():
    print("="*90)
    print("测试组合34（趋势分析 + 网格测试）在不同参数下的结果")
    print("="*90)

    # 当前参数
    test_combination_34((20, 2.0, 0.1, 120, 1.5), "【当前参数】")

    # 宽松参数组合
    test_combination_34((20, 2.0, 0.3, 120, 1.2), "【宽松1】quantile=0.3, vol_ratio=1.2")
    test_combination_34((20, 2.0, 0.4, 120, 1.0), "【宽松2】quantile=0.4, vol_ratio=1.0")
    test_combination_34((20, 2.0, 0.5, 90, 1.0), "【宽松3】quantile=0.5, vol_ratio=1.0, window=90")

    print("\n" + "="*90)


if __name__ == "__main__":
    main()
