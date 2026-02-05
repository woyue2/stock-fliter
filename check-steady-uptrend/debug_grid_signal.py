# -*- coding: utf-8 -*-
"""
调试脚本：测试网格测试信号筛选
"""
from pathlib import Path
from dataclasses import dataclass

import pandas as pd
from data_loader import load_daily_data
from grid_test_vol_contraction import bollinger_bands, volume_ratio


@dataclass
class GridCombo:
    """网格最优参数组合"""
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
            print(f"  {code}: 无信号（低波动&突破&成交量）")
            return False

        last_date = df["date"].iloc[-1]
        cutoff = last_date - pd.Timedelta(days=lookback_days)
        recent = df[signal & (df["date"] >= cutoff)]

        if recent.empty:
            # 统计最近的信号
            all_signal_dates = df[signal]["date"]
            if len(all_signal_dates) > 0:
                last_signal_date = all_signal_dates.max()
                days_since = (last_date - last_signal_date).days
                print(f"  {code}: 最近的信号在 {days_since} 天前（超过{lookback_days}天阈值）")
            else:
                print(f"  {code}: 无信号")
            return False

        print(f"  {code}: ✓ 最近{lookback_days}天内有信号")
        return True
    except Exception as e:
        print(f"  {code}: 异常 - {e}")
        return False


def main():
    # 使用网格测试报告中的最优参数（20天收益周期）
    combo = GridCombo(
        bb_window=20,
        num_std=2.0,
        quantile=0.1,
        quantile_window=120,
        vol_ratio_threshold=1.5,
        horizon=20
    )

    lookback_days = 120
    min_bars = 120

    print(f"测试参数：")
    print(f"  bb_window={combo.bb_window}, num_std={combo.num_std}")
    print(f"  quantile={combo.quantile}, quantile_window={combo.quantile_window}")
    print(f"  vol_ratio_threshold={combo.vol_ratio_threshold}")
    print(f"  lookback_days={lookback_days}, min_bars={min_bars}")
    print()

    # 读取趋势分析结果，选取一些有玄学信号的股票进行测试
    trend_df = pd.read_csv("output/2026-01-23/21-35-49/trend_rules_detail_20260205_213739.csv")
    mystic_df = trend_df[trend_df["玄学_最近6天连续阳线"] == True].head(20)

    print(f"测试 {len(mystic_df)} 只有玄学信号的股票...\n")

    count = 0
    for _, row in mystic_df.iterrows():
        code = str(row["代码"])
        if has_vol_contraction_signal(code, combo, lookback_days, min_bars):
            count += 1

    print(f"\n总结：{count}/{len(mystic_df)} 只股票有网格测试信号")


if __name__ == "__main__":
    main()
