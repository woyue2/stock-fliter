# -*- coding: utf-8 -*-
"""
扫描稳步上升（steady uptrend）信号
使用 just-stock-down 的本地数据，不执行任何抓取
"""
import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from data_loader import iter_stock_items, load_daily_data
from indicators import SteadyUptrendConfig, steady_uptrend_signal


def scan_market(limit: int | None = None, only_signal: bool = False) -> pd.DataFrame:
    config = SteadyUptrendConfig()
    results = []

    for item in iter_stock_items(limit=limit):
        df = load_daily_data(item.code)
        if df.empty:
            continue

        signal = steady_uptrend_signal(df, config)
        row = {
            "code": item.code,
            "name": item.name,
            "latest_date": pd.Timestamp(signal.get("latest_date")).strftime("%Y-%m-%d") if signal.get("latest_date") is not None else "",
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
        if not only_signal or row["steady_uptrend"]:
            results.append(row)

    return pd.DataFrame(results)


def main() -> int:
    parser = argparse.ArgumentParser(description="稳步上升（steady uptrend）扫描")
    parser.add_argument("--limit", type=int, default=None, help="限制扫描数量")
    parser.add_argument("--only-signal", action="store_true", help="只输出满足稳步上升的股票")
    parser.add_argument("--output", type=str, default=None, help="输出CSV路径")
    args = parser.parse_args()

    df = scan_market(limit=args.limit, only_signal=args.only_signal)
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.output:
        output_path = Path(args.output)
    else:
        now = datetime.now()
        batch_date = now.strftime("%Y-%m-%d")
        batch_time = now.strftime("%H-%M-%S")
        batch_dir = output_dir / batch_date / batch_time
        batch_dir.mkdir(parents=True, exist_ok=True)
        
        name = "steady_uptrend_only" if args.only_signal else "steady_uptrend_all"
        output_path = batch_dir / f"{name}_{now.strftime('%Y%m%d_%H%M%S')}.csv"

    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[OK] 输出完成: {output_path}")
    print(f"[CHART] 结果数量: {len(df)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
