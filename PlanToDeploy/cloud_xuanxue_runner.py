# -*- coding: utf-8 -*-
"""
云端玄学组合 Runner

目标:
- 仅复用 check-steady-uptrend 已经算好的稳步上升/趋势/网格结果,
  在 PlanToDeploy/output/cloud_steady 下重新跑一遍 XuanxueCombiner,
  生成“云端版玄学组合报告”, 而不再改动原本的 output 目录。

关键点:
- 输入: 仍从 check-steady-uptrend/output 里读取最新的
  steady_uptrend_*.csv / trend_rules_detail_*.csv / vol_contraction_grid_summary_*.csv
- 输出: 所有玄学组合 CSV + MD + HTML 汇总都写到
  PlanToDeploy/output/cloud_steady/日期/时间/ 下
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
STEADY_ROOT = BASE_DIR / "check-steady-uptrend"
CLOUD_STEADY_OUTPUT = BASE_DIR / "PlanToDeploy" / "output" / "cloud_steady"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="云端玄学组合 Runner(基于现有稳步上升/趋势/网格结果)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="分析截止日期 (YYYY-MM-DD), 例如 2026-02-03; 不填则自动用最近一批结果",
    )
    parser.add_argument(
        "--grid-horizon",
        type=int,
        default=20,
        help="网格测试收益周期(需与原分析使用的一致, 默认 20)",
    )
    return parser.parse_args()


def _patch_cloud_module_label(end_date: str, summary_path: Path) -> None:
    """
    将本次云端玄学组合写入 stocks_index.csv 的记录的「模块」改成“玄学(云端)”,
    以便在搜索和前端中与本地稳步上升结果区分。
    """
    if not end_date:
        return

    date_folder = end_date
    index_dir = BASE_DIR / "get-data" / "data" / "stocks_index" / date_folder
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
    args = parse_args()

    if not STEADY_ROOT.exists():
        print(f"[cloud_xuanxue] 未找到目录: {STEADY_ROOT}")
        return 1

    # 将 check-steady-uptrend 加入 sys.path, 以便复用内部 Pipeline/XuanxueCombiner
    if str(STEADY_ROOT) not in sys.path:
        sys.path.insert(0, str(STEADY_ROOT))

    from pipeline import Pipeline, PipelineConfig  # type: ignore

    CLOUD_STEADY_OUTPUT.mkdir(parents=True, exist_ok=True)

    # 1) 先用原 output 目录读取“已有分析结果”
    original_output_dir = STEADY_ROOT / "output"

    config = PipelineConfig(
        use_steady_uptrend=True,
        use_trend_analysis=True,
        use_grid_test=True,
        use_mystic=True,
        grid_horizon=args.grid_horizon,
        limit=None,
        output_dir=original_output_dir,
        end_date=args.end_date,
    )

    pipeline = Pipeline(config)

    # 只做“加载已有结果”, 不重算指标
    pipeline._load_existing_results()

    if pipeline.result.trend_analysis is None or pipeline.result.steady_uptrend is None:
        print("[cloud_xuanxue] 未找到已有的趋势/稳步上升结果, 请先在原模块跑一遍完整分析")
        return 1

    # 2) 将输出目录切换到 PlanToDeploy/output/cloud_steady, 重新设置 batch_dir
    pipeline.config.output_dir = CLOUD_STEADY_OUTPUT
    pipeline._setup_batch_dir()

    # 在新的 batch_dir 下重新做组合 + 报告(这一步会调用 XuanxueCombiner)
    pipeline._combine_results()
    pipeline._generate_reports()

    # 找到本次云端玄学的 summary_*.html, 用于定位索引中的记录
    batch_dir = pipeline.result.batch_dir
    summary_files = sorted(batch_dir.glob("summary_*.html"), reverse=True)
    if summary_files and args.end_date:
        _patch_cloud_module_label(args.end_date, summary_files[0])

    print("[cloud_xuanxue] 玄学组合执行完成, 输出目录:", batch_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
