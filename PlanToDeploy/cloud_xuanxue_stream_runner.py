# -*- coding: utf-8 -*-
"""
云端玄学组合 Stream Runner

目标:
- 不再依赖 check-steady-uptrend/output 里已有的 CSV 结果
- 直接在云端通过「流式拉取日线」+ 原有稳步上升 / 趋势 / 网格逻辑
  重新计算玄学组合, 并将所有结果输出到 PlanToDeploy/output/cloud_xuanxue 下

实现要点:
- 股票池: 复用 util.stream_fetch.load_stock_pool_from_selected_all
  - 默认使用 get-data/data/selected_stocks_all.csv
  - 测试模式(--test) 使用 PlanToDeploy/selected_stocks_all copy.csv
- 数据来源: 通过 util.stream_fetch.fetch_daily_data_streaming
  - 使用 --days / --end-date 控制时间窗口
- 计算逻辑: 直接复用 check-steady-uptrend/pipeline.Pipeline
  - 通过运行时 monkey-patch data_loader.iter_stock_items / load_daily_data
    让 Pipeline 内部所有分析器使用「流式数据」而不是本地 RAW CSV
- 输出:
  - 玄学组合 HTML/MD/CSV 以及汇总 summary_*.html 均落在:
    PlanToDeploy/output/cloud_xuanxue/<date>/<time>/
  - 同时写入 stocks_index, 模块名统一标记为「玄学(云端)」
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd


# 在云端部署场景下, PlanToDeploy 作为项目根目录
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
from stream_run_daily import _build_global_reports_index  # type: ignore

STEADY_ROOT = BASE_DIR / "check-steady-uptrend"
CLOUD_XUANXUE_OUTPUT = BASE_DIR / "output" / "cloud_xuanxue"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="云端玄学组合 Stream Runner(基于流式日线 + 原始 Pipeline)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="分析截止日期 (YYYY-MM-DD), 不填则使用数据最新日期",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="回看天数窗口(流式拉数使用, 默认365天)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制股票池数量(仅用于测试/云端小样本调试)",
    )
    parser.add_argument(
        "--grid-horizon",
        type=int,
        default=20,
        help="网格测试收益周期(需与本地配置一致, 默认20)",
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
        help="自定义股票池 CSV 路径, 覆盖 --test 的默认路径",
    )
    return parser.parse_args()


def _build_stock_pool(
    args: argparse.Namespace,
) -> tuple[List[StockInfo], Dict[str, StockInfo], Path]:
    """
    构建股票池及 code -> StockInfo 映射, 返回:
    - stocks: StockInfo 列表
    - stock_map: 代码(6位) -> StockInfo
    - selected_path: 实际使用的股票池文件路径(仅用于日志)
    """
    if args.stocks_file:
        selected_path = Path(args.stocks_file)
    elif args.test:
        selected_path = BASE_DIR / "selected_stocks_all copy.csv"
    else:
        # 默认 read-only SSOT
        selected_path = None

    stocks = load_stock_pool_from_selected_all(
        selected_path=selected_path,
        limit=args.limit,
    )
    if selected_path is None:
        selected_path = BASE_DIR / "selected_stocks_all.csv"

    stock_map: Dict[str, StockInfo] = {s.code: s for s in stocks}
    return stocks, stock_map, selected_path


def _patch_data_loader(
    stocks: List[StockInfo],
    stock_map: Dict[str, StockInfo],
    days: int,
    end_date: Optional[str],
) -> None:
    """
    将 check-steady-uptrend/data_loader 中的 iter_stock_items / load_daily_data
    在当前进程内替换为“基于流式拉数”的实现, 只影响当前 Runner。
    """
    if str(STEADY_ROOT) not in sys.path:
        sys.path.insert(0, str(STEADY_ROOT))

    # 延迟导入, 确保 sys.path 已包含 check-steady-uptrend
    import data_loader as steady_data_loader  # type: ignore
    from data_loader import StockItem  # type: ignore

    # 1) 覆盖 iter_stock_items: 直接使用我们构建的股票池
    def iter_stock_items_stream(limit: int | None = None) -> Iterable[StockItem]:
        if limit is not None and limit > 0:
            items = stocks[:limit]
        else:
            items = stocks
        for s in items:
            yield StockItem(
                code=s.code,
                name=s.name,
                bs_code=s.bs_code,
                industry=s.industry,
            )

    # 2) 覆盖 load_daily_data: 完全走 fetch_daily_data_streaming
    def load_daily_data_streaming(code: str) -> pd.DataFrame:
        code6 = str(code).zfill(6)
        info = stock_map.get(code6)
        if info is not None:
            bs_code = info.bs_code
        else:
            prefix = "sh" if code6.startswith("6") else "sz"
            bs_code = f"{prefix}.{code6}"

        df = fetch_daily_data_streaming(
            code=code6,
            bs_code=bs_code,
            days=days,
            end_date=end_date,
        )
        if df is None:
            return pd.DataFrame()

        # Pipeline 期望的列名/类型与 util.stream_fetch 已对齐(date/open/high/low/close/volume)
        return df.copy()

    # 真正打补丁
    steady_data_loader.iter_stock_items = iter_stock_items_stream  # type: ignore[assignment]
    steady_data_loader.load_daily_data = load_daily_data_streaming  # type: ignore[assignment]


def _patch_cloud_module_label(end_date: str, summary_path: Path) -> None:
    """
    将本次云端玄学组合写入 stocks_index.csv 的记录的「模块」改成“玄学(云端)”,
    以便在搜索和前端中与本地稳步上升结果区分。
    """
    if not end_date:
        return

    date_folder = end_date
    # 云端模式下, 索引统一写入 PlanToDeploy/stocks_index
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

    df.loc[mask, "模块"] = "玄学(云端)"
    df.to_csv(index_file, index=False, encoding="utf-8-sig")


def main() -> int:
    args = _parse_args()

    if not STEADY_ROOT.exists():
        print(f"[cloud_xuanxue_stream] 未找到目录: {STEADY_ROOT}")
        return 1

    # 1) 构建股票池 + code -> StockInfo 映射
    stocks, stock_map, selected_path = _build_stock_pool(args)
    if not stocks:
        print("[cloud_xuanxue_stream] 股票池为空, 无需执行玄学组合分析")
        return 0

    print(f"[cloud_xuanxue_stream] 使用股票池文件: {selected_path}")
    print(f"[cloud_xuanxue_stream] 股票池数量: {len(stocks)}")

    # 2) 为当前进程打补丁, 让 Pipeline 使用流式数据
    _patch_data_loader(
        stocks=stocks,
        stock_map=stock_map,
        days=args.days,
        end_date=args.end_date,
    )

    # 3) 导入 Pipeline, 构造配置
    from pipeline import Pipeline, PipelineConfig  # type: ignore

    CLOUD_XUANXUE_OUTPUT.mkdir(parents=True, exist_ok=True)

    config = PipelineConfig(
        use_steady_uptrend=True,
        use_trend_analysis=True,
        use_grid_test=True,
        use_mystic=True,
        grid_horizon=args.grid_horizon,
        lookback_days=120,
        min_bars=120,
        limit=args.limit,
        output_dir=CLOUD_XUANXUE_OUTPUT,
        end_date=args.end_date,
    )

    pipeline = Pipeline(config)

    # 4) 登录 BaoStock(如可用) + 运行完整流水线
    login_baostock()
    try:
        ret = pipeline.run_full()
    finally:
        logout_baostock()

    # 5) 找到本次云端玄学的 summary_*.html, 调整索引中的模块名
    batch_dir = pipeline.result.batch_dir
    if isinstance(batch_dir, Path):
        summary_files = sorted(batch_dir.glob("summary_*.html"), reverse=True)
        if summary_files and args.end_date:
            _patch_cloud_module_label(args.end_date, summary_files[0])
        print("[cloud_xuanxue_stream] 输出目录:", batch_dir)
    else:
        print("[cloud_xuanxue_stream] 未能确定本次批次输出目录")

    # 6) 重新构建索引 & 云端统一入口
    try:
        _build_global_reports_index()
    except Exception as exc:
        print(f"[cloud_xuanxue_stream] 重建报告索引失败(不影响本次分析结果): {exc}")

    return int(ret or 0)


if __name__ == "__main__":
    raise SystemExit(main())
