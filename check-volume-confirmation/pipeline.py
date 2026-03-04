# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  limit/generate_html/generate_markdown/auto_open/show_progress/end_date 参数
# OUTPUT: Dict — {scanned, matched, skipped, skip_reasons, files}
# POS:    check-volume-confirmation/pipeline.py
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
from analyzers import evaluate_stock, empty_result_df  # Phase 6: 分离到 analyzers/
from reporters import generate_html_report, generate_markdown_report
from shipan_logic import analyze_shipan_behavior



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
    matched_rows: list[dict] = []
    all_rows: list[dict] = []
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

        # 获取分析数据，开启 return_all 模式（只要数据有效就返回指标）
        data, reason = evaluate_stock(df, end_date=end_date, return_all=True)
        if reason:
            skip_reasons[reason] += 1
            continue

        # 补全基础信息
        stock_info = info_map.get(code, {})
        data["name"] = stock_info.get("name", code)
        data["industry"] = stock_info.get("industry", "未知") or "未知"
        data["board"] = infer_board(code)

        # 全市场列表
        all_rows.append(data)

        # 如果符合策略条件，加入匹配列表
        if data.get("is_hit"):
            matched_rows.append(data)
            # 更新报告日期
            current_date = pd.to_datetime(data["date_0"])
            max_date = current_date if max_date is None else max(max_date, current_date)

    matched_df = pd.DataFrame(matched_rows) if matched_rows else empty_result_df()
    all_df = pd.DataFrame(all_rows) if all_rows else empty_result_df()

    def sort_df(df_in):
        if df_in.empty: return df_in
        return df_in.sort_values(
            ["confidence", "date_0", "code"], 
            ascending=[False, False, True]
        ).reset_index(drop=True)

    matched_df = sort_df(matched_df)
    all_df = sort_df(all_df)

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
            full_market_df=all_df,
        )
        result["files"]["html"] = str(html_path)
        if auto_open:
            webbrowser.open(html_path.as_uri())

    return result
