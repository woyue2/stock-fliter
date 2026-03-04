# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional
import webbrowser

import pandas as pd
try:
    from tqdm import tqdm
except Exception:
    tqdm = None

from data_loader import (
    OUTPUT_DIR,
    ensure_dirs,
    infer_board,
    list_raw_files,
    load_stock_df,
    load_stock_info_map,
)
from reporters import generate_html_report, generate_markdown_report
from shipan_logic import analyze_shipan_behavior


def _evaluate_stock(df: pd.DataFrame, end_date: Optional[str] = None) -> tuple[Optional[dict], Optional[str]]:
    if df is None or df.empty:
        return None, "无数据"

    # 如果指定了结束日期，截断数据
    if end_date:
        try:
            target_dt = pd.to_datetime(end_date)
            df = df[df["date"] <= target_dt].copy()
        except Exception:
            return None, "结束日期格式错误"

    if len(df) < 5:
        return None, "样本不足5天"

    last5 = df.tail(5).copy()
    if last5[["open", "close", "volume"]].isna().any().any():
        return None, "关键值缺失"
    if (last5["volume"] <= 0).any():
        return None, "成交量无效"

    d0 = last5.iloc[-1]   # 今天
    d1 = last5.iloc[-2]   # 昨天
    d2 = last5.iloc[-3]
    d3 = last5.iloc[-4]
    d4 = last5.iloc[-5]

    # 核心限制：量过前高 (昨放量)
    yday_breakout = bool(d1["volume"] > d2["volume"] and d1["volume"] > d3["volume"] and d1["volume"] > d4["volume"])
    today_up = bool(d0["close"] > d0["open"])

    if not (yday_breakout and today_up):
        reason = "非昨放量" if not yday_breakout else "今日非阳线"
        return None, reason

    # 计算试盘行为
    shipan_count, shipan_detail = analyze_shipan_behavior(df)

    return {
        "code": str(d0["code"]).zfill(6),
        "date_0": pd.Timestamp(d0["date"]).strftime("%Y-%m-%d"),
        "open_0": float(d0["open"]),
        "close_0": float(d0["close"]),
        "volume_0": float(d0["volume"]),
        "date_m1": pd.Timestamp(d1["date"]).strftime("%Y-%m-%d"),
        "volume_m1": float(d1["volume"]),
        "volume_m2": float(d2["volume"]),
        "volume_m3": float(d3["volume"]),
        "volume_m4": float(d4["volume"]),
        "shipan_count": shipan_count,
        "shipan_detail": shipan_detail,
        "signal": "昨放量+今阳线",
    }, None


def _empty_result_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "code",
            "name",
            "industry",
            "board",
            "date_0",
            "open_0",
            "close_0",
            "volume_0",
            "date_m1",
            "volume_m1",
            "volume_m2",
            "volume_m3",
            "volume_m4",
            "shipan_count",
            "shipan_detail",
            "signal",
        ]
    )


def run_pipeline(
    limit: Optional[int] = None,
    generate_html: bool = True,
    generate_markdown: bool = True,
    auto_open: bool = True,
    show_progress: bool = True,
    end_date: Optional[str] = None,
) -> dict:
    ensure_dirs()
    info_map = load_stock_info_map()

    files = list_raw_files(limit=limit)
    skip_reasons: Counter[str] = Counter()
    rows: list[dict] = []
    max_date: Optional[pd.Timestamp] = None

    iterator = files
    if show_progress and tqdm is not None:
        iterator = tqdm(files, total=len(files), desc="扫描进度", unit="只")

    for path in iterator:
        code = path.stem.zfill(6)
        df, error = load_stock_df(path)
        if error:
            skip_reasons[error] += 1
            continue

        hit, reason = _evaluate_stock(df, end_date=end_date)
        if reason:
            skip_reasons[reason] += 1
            continue

        # 使用 hit 中的日期更新 max_date
        current_date = pd.to_datetime(hit["date_0"])
        max_date = current_date if max_date is None else max(max_date, current_date)

        stock_info = info_map.get(code, {})
        hit["name"] = stock_info.get("name", code)
        hit["industry"] = stock_info.get("industry", "未知") or "未知"
        hit["board"] = infer_board(code)
        rows.append(hit)

    matched_df = _empty_result_df() if not rows else pd.DataFrame(rows)
    if not matched_df.empty:
        # 首先按试盘次数倒序，然后按日期降序，最后按代码升序
        matched_df = matched_df.sort_values(
            ["shipan_count", "date_0", "code"], 
            ascending=[False, False, True]
        ).reset_index(drop=True)

    report_day = max_date.strftime("%Y-%m-%d") if max_date is not None else datetime.now().strftime("%Y-%m-%d")
    time_dir = datetime.now().strftime("%H-%M-%S")
    output_dir = OUTPUT_DIR / report_day / time_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "volume_confirmation.csv"
    matched_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    result = {
        "scanned": len(files),
        "matched": len(matched_df),
        "skipped": int(sum(skip_reasons.values())),
        "skip_reasons": dict(skip_reasons),
        "files": {"csv": str(csv_path)},
    }

    title = "量价确认报告"
    report_date = report_day.replace("-", "")

    if generate_markdown:
        md_path = generate_markdown_report(matched_df, output_dir=output_dir, title=title, report_date=report_date)
        result["files"]["markdown"] = str(md_path)

    if generate_html:
        html_path = generate_html_report(
            matched_df,
            output_dir=output_dir,
            title=title,
            report_date=report_date,
            module_name="量价确认",
            strategy_name="昨放量+今阳线",
        )
        result["files"]["html"] = str(html_path)
        if auto_open:
            webbrowser.open(html_path.as_uri())

    return result
