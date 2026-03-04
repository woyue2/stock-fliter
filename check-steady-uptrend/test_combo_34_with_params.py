# -*- coding: utf-8 -*-
"""
测试组合34使用不同参数的效果
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


def test_combo_34(combo, label):
    """测试组合34"""
    trend_df = pd.read_csv("output/2026-01-23/22-02-51/trend_rules_detail_20260205_220433.csv")

    # 趋势分析筛选
    trend_mask = (
        trend_df.get("趋势跟随_是否信号", False)
        | trend_df.get("上升回撤_是否信号", False)
        | trend_df.get("波动收缩突破_是否信号", False)
    )
    trend_candidates = trend_df[trend_mask].copy()

    # 再筛选网格测试信号
    count_6up = 0
    count_6up1down = 0

    for _, row in trend_candidates.iterrows():
        code = str(row["代码"])
        if has_vol_contraction_signal(code, combo, 120, 120):
            if row.get("玄学_最近6天连续阳线", False):
                count_6up += 1
            if row.get("玄学_10天内有6连阳后1阴", False):
                count_6up1down += 1

    print(f"{label:50s} | 6连阳: {count_6up:3d}只 | 近10天6涨1跌: {count_6up1down:3d}只")


def main():
    print("="*90)
    print("测试组合34（趋势分析 + 网格测试）")
    print("="*90)

    lookback_days = 120
    min_bars = 120

    # 测试前5名的参数
    params_list = [
        (0.2, 60, 1.5, "第1名: q=0.2, w=60, vol=1.5 (avg=2.79%)"),
        (0.2, 60, 1.2, "第2名: q=0.2, w=60, vol=1.2 (avg=2.72%)"),
        (0.2, 60, 1.0, "第3名: q=0.2, w=60, vol=1.0 (avg=2.65%)"),
        (0.3, 60, 1.5, "第4名: q=0.3, w=60, vol=1.5 (avg=2.29%)"),
        (0.2, 120, 1.2, "第5名: q=0.2, w=120, vol=1.2 (avg=2.25%)"),
    ]

    for q, w, v, label in params_list:
        combo = GridCombo(
            bb_window=20,
            num_std=2.0,
            quantile=q,
            quantile_window=w,
            vol_ratio_threshold=v,
            horizon=20
        )
        test_combo_34(combo, label)

    print("="*90)


if __name__ == "__main__":
    main()
