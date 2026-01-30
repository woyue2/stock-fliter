# -*- coding: utf-8 -*-
"""
随机抽样验证稳步上升策略
- 不抓取数据，仅使用 just-stock-down/data/raw
- 在最近窗口中找出最新信号，并计算未来收益
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from data_loader import iter_stock_items, sample_stock_items, load_daily_data
from indicators import SteadyUptrendConfig, compute_steady_uptrend_flags


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


def validate_samples(sample_size: int, seed: int, lookback_days: int, horizons: List[int]) -> pd.DataFrame:
    config = SteadyUptrendConfig()
    items = sample_stock_items(sample_size, seed=seed)
    return _validate_items(items, lookback_days, horizons, config)


def validate_all(lookback_days: int, horizons: List[int], limit: int | None = None) -> pd.DataFrame:
    config = SteadyUptrendConfig()
    items = list(iter_stock_items(limit=limit))
    return _validate_items(items, lookback_days, horizons, config)


def _validate_items(items, lookback_days: int, horizons: List[int], config: SteadyUptrendConfig) -> pd.DataFrame:
    records = []

    for item in items:
        df = load_daily_data(item.code)
        if df.empty or len(df) < config.min_bars:
            records.append({
                "code": item.code,
                "name": item.name,
                "status": "数据不足",
            })
            continue

        df_flags = compute_steady_uptrend_flags(df, config)
        df_flags = df_flags.reset_index(drop=True)
        df_flags["date"] = pd.to_datetime(df_flags["date"])

        last_date = df_flags["date"].iloc[-1]
        cutoff = last_date - pd.Timedelta(days=lookback_days)

        recent_signals = df_flags[(df_flags["steady_uptrend"] == True) & (df_flags["date"] >= cutoff)]
        if recent_signals.empty:
            records.append({
                "code": item.code,
                "name": item.name,
                "status": "近期无信号",
            })
            continue

        signal_row = recent_signals.iloc[-1]
        signal_idx = int(signal_row.name)
        close_series = df_flags["close"].astype(float)
        forward_returns = compute_forward_returns(close_series, signal_idx, horizons)

        row = {
            "code": item.code,
            "name": item.name,
            "status": "有信号",
            "signal_date": pd.Timestamp(signal_row["date"]).strftime("%Y-%m-%d"),
            "signal_close": float(signal_row["close"]),
        }
        for h, val in forward_returns.items():
            row[f"ret_{h}"] = val
        records.append(row)

    return pd.DataFrame(records)


def summarize_validation(df: pd.DataFrame, horizons: List[int]) -> pd.DataFrame:
    rows = []
    signal_df = df[df["status"] == "有信号"].copy()
    for h in horizons:
        col = f"ret_{h}"
        valid = signal_df[signal_df[col].notna()]
        if valid.empty:
            rows.append({
                "horizon": h,
                "count": 0,
                "hit_rate": None,
                "avg_return": None,
            })
            continue
        hit_rate = float((valid[col] > 0).mean())
        avg_return = float(valid[col].mean())
        rows.append({
            "horizon": h,
            "count": int(len(valid)),
            "hit_rate": hit_rate,
            "avg_return": avg_return,
        })
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="随机抽样验证稳步上升策略")
    parser.add_argument("--samples", type=int, default=12, help="随机抽样股票数量")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--lookback", type=int, default=120, help="信号回看天数")
    parser.add_argument("--horizons", type=str, default="5,20,60", help="收益区间，如 5,20,60")
    parser.add_argument("--all", action="store_true", help="分析全部股票（使用本地数据）")
    parser.add_argument("--limit", type=int, default=None, help="全部模式下限制股票数量")
    args = parser.parse_args()

    horizons = [int(h.strip()) for h in args.horizons.split(",") if h.strip()]

    if args.all:
        df = validate_all(args.lookback, horizons, limit=args.limit)
    else:
        df = validate_samples(args.samples, args.seed, args.lookback, horizons)
    summary = summarize_validation(df, horizons)

    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    batch_date = now.strftime("%Y-%m-%d")
    batch_time = now.strftime("%H-%M-%S")
    batch_dir = output_dir / batch_date / batch_time
    batch_dir.mkdir(parents=True, exist_ok=True)

    detail_path = batch_dir / f"validation_detail_{ts}.csv"
    summary_path = batch_dir / f"validation_summary_{ts}.csv"
    report_path = batch_dir / f"validation_report_{ts}.md"

    df.to_csv(detail_path, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 稳步上升策略随机抽样验证报告 ({ts})\n\n")
        if args.all:
            f.write(f"- 全市场模式: 是\n")
            if args.limit:
                f.write(f"- 限制数量: {args.limit}\n")
        else:
            f.write(f"- 抽样数量: {args.samples}\n")
        f.write(f"- 信号回看天数: {args.lookback}\n")
        f.write(f"- 收益区间: {', '.join(map(str, horizons))}\n\n")
        f.write("## 汇总统计\n\n")
        f.write(summary.to_markdown(index=False))
        f.write("\n\n## 详细样本\n\n")
        f.write(df.to_markdown(index=False))

    print(f"[OK] 验证完成：{detail_path}")
    print(f"[OK] 汇总输出：{summary_path}")
    print(f"[OK] 报告输出：{report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
