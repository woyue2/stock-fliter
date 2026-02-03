# -*- coding: utf-8 -*-
"""
云端 新指标 Stream Runner

目标:
- 在 PlanToDeploy 下提供一个“只跑新指标(云端)”的轻量入口
- 复用 stream_run_daily 的流式拉数逻辑和 check-new-indicators 的分析/报告结构

特性:
- 股票池: 只读 selected_stocks_all.csv (或 --test 时使用 PlanToDeploy/selected_stocks_all copy.csv)
- 数据获取: util.stream_fetch.fetch_daily_data_streaming (BaoStock 优先, 失败回退腾讯日K)
- 输出: PlanToDeploy/output/cloud_new/<date>/<time>/...
- 索引: 写入 stocks_index/<date>/stocks_index.csv, 模块标记为“新指标(云端)”
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


# 云端部署场景下, PlanToDeploy 作为项目根目录
BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from util.stream_fetch import (  # type: ignore
    StockInfo,
    fetch_daily_data_streaming,
    load_stock_pool_from_selected_all,
    login_baostock,
    logout_baostock,
)
from stream_run_daily import (  # type: ignore
    _import_new_dependencies,
    _analyze_new_single,
    _build_new_reports,
    _build_global_reports_index,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="云端 新指标 Stream Runner (仅跑新指标模块)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="分析截止日期 (YYYY-MM-DD), 默认为今天",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="回看天数窗口(默认 365 天)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制股票池数量(仅用于测试)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="测试模式: 使用 PlanToDeploy/selected_stocks_all copy.csv 作为股票池",
    )
    parser.add_argument(
        "--stocks-file",
        type=str,
        default=None,
        help="自定义股票池 CSV 路径, 默认使用 get-data/data/selected_stocks_all.csv",
    )
    return parser.parse_args()


def _build_stock_pool(args: argparse.Namespace) -> tuple[List[StockInfo], Path]:
    """根据参数构建股票池与实际使用的股票池文件路径。"""
    if args.stocks_file:
        selected_path = Path(args.stocks_file)
    elif args.test:
        selected_path = BASE_DIR / "selected_stocks_all copy.csv"
    else:
        selected_path = None

    stocks = load_stock_pool_from_selected_all(
        selected_path=selected_path,
        limit=args.limit,
    )

    if selected_path is None:
        selected_path = BASE_DIR / "selected_stocks_all.csv"

    return stocks, selected_path


def _patch_new_module_label(end_date: str, summary_path: Path) -> None:
    """
    将本次云端新指标写入 stocks_index.csv 的记录的「模块」改成“新指标(云端)”，
    以便在搜索和前端中与本地新指标结果区分。
    """
    if not end_date:
        return

    date_folder = end_date
    index_dir = BASE_DIR / "stocks_index" / date_folder
    index_file = index_dir / "stocks_index.csv"
    if not index_file.exists():
        return

    try:
        df = pd.read_csv(index_file, dtype=str)
    except Exception:
        return

    if df.empty or "报告路径" not in df.columns or "模块" not in df.columns:
        return

    project_root = BASE_DIR
    try:
        relative_path = summary_path.relative_to(project_root)
    except ValueError:
        return

    web_path = str(relative_path).replace("\\", "/")
    mask = df["报告路径"].astype(str).str.strip() == web_path
    if not mask.any():
        return

    df.loc[mask, "模块"] = "新指标(云端)"
    df.to_csv(index_file, index=False, encoding="utf-8-sig")


def main() -> int:
    args = _parse_args()

    # 1) 加载股票池
    stocks, selected_path = _build_stock_pool(args)
    if not stocks:
        print("[cloud_new_stream] 股票池为空, 无需执行新指标分析")
        return 0

    print(f"[cloud_new_stream] 使用股票池文件: {selected_path}")
    print(f"[cloud_new_stream] 股票池数量: {len(stocks)}")

    # 2) 导入新指标依赖
    StockAnalyzer, NewReporter = _import_new_dependencies()

    new_results: List[Dict] = []
    global_max_date: Optional[datetime] = None

    # 3) 流式拉数 + 新指标分析
    login_baostock()
    try:
        for idx, stock in enumerate(stocks, 1):
            df_daily = fetch_daily_data_streaming(
                code=stock.code,
                bs_code=stock.bs_code,
                days=args.days,
                end_date=args.end_date,
            )
            if df_daily is None or df_daily.empty:
                continue

            latest_date = df_daily["date"].max()
            if pd.notna(latest_date):
                latest_dt = pd.Timestamp(latest_date)
                if global_max_date is None or latest_dt > global_max_date:
                    global_max_date = latest_dt

            new_row = _analyze_new_single(df_daily, stock, StockAnalyzer)
            if new_row is not None:
                new_results.append(new_row)

            del df_daily
    finally:
        logout_baostock()

    # 4) 确定分析日期
    if args.end_date:
        analysis_date = args.end_date
    elif global_max_date is not None:
        analysis_date = pd.Timestamp(global_max_date).strftime("%Y-%m-%d")
    else:
        analysis_date = datetime.now().strftime("%Y-%m-%d")

    print(f"[cloud_new_stream] 本次分析日期: {analysis_date}")

    if not new_results:
        print("[cloud_new_stream] 当日无新指标命中结果, 跳过报告生成")
        return 0

    # 5) 生成云端新指标报告 + 索引
    summary_path = _build_new_reports(
        new_results,
        analysis_date,
        NewReporter,
    )

    if isinstance(summary_path, Path):
        _patch_new_module_label(analysis_date, summary_path)
        print("[cloud_new_stream] 输出 HTML 总览:", summary_path)

    # 6) 重新构建索引 & 云端统一入口
    try:
        _build_global_reports_index()
    except Exception as exc:
        print(f"[cloud_new_stream] 重建报告索引失败(不影响本次分析结果): {exc}")

    print("[cloud_new_stream] 新指标云端 Runner 执行完毕")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
