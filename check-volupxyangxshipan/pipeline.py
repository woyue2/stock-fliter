# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  limit/generate_html/generate_markdown/auto_open/show_progress/end_date 参数
# OUTPUT: Dict — {scanned, matched, skipped, skip_reasons, files}
# POS:    check-volupxyangxshipan/pipeline.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional
import webbrowser

import pandas as pd
import os
try:
    from tqdm import tqdm
    if os.environ.get("DISABLE_TQDM") == "1":
        tqdm = None
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



from concurrent.futures import ProcessPoolExecutor, as_completed
import sys

# 导入系统工具
_ROOT_DIR = Path(__file__).resolve().parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))
from util.system_utils import get_optimal_worker_count


def _worker_process_stock(path_str: str, end_date: Optional[str], info_map: dict) -> Optional[dict]:
    """子进程执行单个股票分析"""
    path = Path(path_str)
    code = path.stem.zfill(6)
    
    # 获取分析数据
    df, error = load_stock_df(path)
    if error:
        return {"error": error}

    data, reason = evaluate_stock(df, end_date=end_date, return_all=True)
    if reason:
        return {"error": reason}

    # 补全基础信息
    stock_info = info_map.get(code, {})
    data["code"] = code
    data["name"] = stock_info.get("name", code)
    data["industry"] = stock_info.get("industry", "未知") or "未知"
    data["board"] = infer_board(code)
    
    return data


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

    # 计算并行工作进程数
    if os.environ.get("LOW_MEM_MODE") == "1":
        workers = 1
        print("  [INFO] 低内存模式：使用单进程扫描")
    else:
        workers = get_optimal_worker_count()
        if workers > 1:
            print(f"  [INFO] 开启服务器级优化：使用 {workers} 个进程并行扫描")
        else:
            print("  [INFO] 系统资源有限：使用单进程扫描")

    if workers > 1:
        # 并行执行
        results = []
        with ProcessPoolExecutor(max_workers=workers) as executor:
            # 提交任务
            future_to_path = {
                executor.submit(_worker_process_stock, str(p), end_date, info_map): p 
                for p in files
            }
            
            # 进度条
            if show_progress and tqdm is not None:
                pbar = tqdm(total=len(files), desc="并行扫描", unit="只")
            else:
                pbar = None
                
            for future in as_completed(future_to_path):
                res = future.result()
                if res and "error" in res:
                    skip_reasons[res["error"]] += 1
                elif res:
                    results.append(res)
                
                if pbar:
                    pbar.update(1)
            
            if pbar:
                pbar.close()
                
        # 处理结果
        for data in results:
            all_rows.append(data)
            if data.get("is_hit"):
                matched_rows.append(data)
                current_date = pd.to_datetime(data["date_0"])
                max_date = current_date if max_date is None else max(max_date, current_date)
    else:
        # 串行执行（节省内存）
        iterator = files
        if show_progress and tqdm is not None:
            iterator = tqdm(files, total=len(files), desc="扫描进度", unit="只")

        for path in iterator:
            res = _worker_process_stock(str(path), end_date, info_map)
            if res and "error" in res:
                skip_reasons[res["error"]] += 1
            elif res:
                all_rows.append(res)
                if res.get("is_hit"):
                    matched_rows.append(res)
                    current_date = pd.to_datetime(res["date_0"])
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

    csv_path = output_dir / "volupxyangxshipan.csv"
    matched_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    result = {
        "scanned": len(files),
        "matched": len(matched_df),
        "skipped": int(sum(skip_reasons.values())),
        "skip_reasons": dict(skip_reasons),
        "files": {"csv": str(csv_path)},
    }

    title = "VolUp x Yang x Shipan报告"
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
            module_name="VolUp x Yang x Shipan",
            strategy_name="昨放量+今阳线",
            full_market_df=all_df,
        )
        result["files"]["html"] = str(html_path)
        if auto_open:
            print(f"  🌐 自动打开浏览器...")
            url = html_path.as_uri()
            success = webbrowser.open(url)
            if not success and os.name == 'posix':
                # 尝试 WSL 方案
                try:
                    import subprocess
                    subprocess.run(['wslview', url], check=False, capture_output=True)
                except:
                    try:
                        import subprocess
                        subprocess.run(['powershell.exe', '-c', f'start "{url}"'], check=False, capture_output=True)
                    except: pass

    return result
