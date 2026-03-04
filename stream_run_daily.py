# -*- coding: utf-8 -*-
"""
云端轻量 Runner

在 1 核 1G 等低配置环境下, 通过“边拉数据、边分析、用完即丢”的方式
串联 TD 九底 / 稳步上升 / 新指标 三个模块, 并尽量复用现有报告与索引结构。

核心约束:
- 只读 get-data/data/selected_stocks_all.csv, 不改写其生成逻辑
- 不依赖 get-data/data/raw/*.csv 必须存在, 优先走在线拉数
- 结果阶段仍使用各模块原有 output/ 与 stocks_index 目录结构, 方便前端与搜索索引复用
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from util.stream_fetch import (
    StockInfo,
    fetch_daily_data_streaming,
    load_stock_pool_from_selected_all,
    login_baostock,
    logout_baostock,
)


BASE_DIR = Path(__file__).resolve().parent
CLOUD_BASE = BASE_DIR / "PlanToDeploy" / "output"


def _get_board_type(code: str) -> str:
    """根据股票代码判断所属交易板块(与现有模块保持一致)."""
    code = str(code)
    if code.startswith("688"):
        return "科创板"
    if code.startswith("300") or code.startswith("301"):
        return "创业板"
    if code.startswith("8"):
        return "北交所"
    if code.startswith("002") or code.startswith("000"):
        return "深圳主板"
    if code.startswith("60"):
        return "上海主板"
    return "其他"


def _import_td_dependencies():
    """临时将 check-trend-bottom 加入 sys.path, 导入九底相关组件."""
    # 清理可能存在的同名顶层包, 避免与其他模块冲突
    for name in [
        "reporters",
        "reporters.html_reporter",
        "reporters.markdown_reporter",
        "pipeline",
        "data_loader",
    ]:
        sys.modules.pop(name, None)

    td_root = BASE_DIR / "check-trend-bottom"
    inserted = False
    if str(td_root) not in sys.path:
        sys.path.insert(0, str(td_root))
        inserted = True
    try:
        from analyzers.td_analyzer import TDAnalyzer, TDAnalyzerConfig  # type: ignore
        from reporters.html_reporter import HTMLReporter as TDHTMLReporter  # type: ignore
        from reporters.markdown_reporter import MarkdownReporter as TDMarkdownReporter  # type: ignore
    finally:
        if inserted:
            # 移除临时插入的路径, 避免影响后续模块导入
            try:
                sys.path.remove(str(td_root))
            except ValueError:
                pass
    return TDAnalyzer, TDAnalyzerConfig, TDHTMLReporter, TDMarkdownReporter


def _import_steady_dependencies():
    """临时将 check-steady-uptrend 加入 sys.path, 导入稳步上升相关组件."""
    # 清理与 TD 模块可能共享的顶层模块名, 以便重新加载稳步上升专用实现
    for name in [
        "reporters",
        "reporters.html_reporter",
        "reporters.markdown_reporter",
        "pipeline",
        "data_loader",
    ]:
        sys.modules.pop(name, None)
    steady_root = BASE_DIR / "check-steady-uptrend"
    inserted = False
    if str(steady_root) not in sys.path:
        sys.path.insert(0, str(steady_root))
        inserted = True
    try:
        from indicators import SteadyUptrendConfig, steady_uptrend_signal  # type: ignore
        from reporters.html_reporter import HtmlReporter as SteadyHtmlReporter  # type: ignore
        from reporters.markdown_reporter import MarkdownReporter as SteadyMarkdownReporter  # type: ignore
        from pipeline import AnalysisResult, PipelineResult  # type: ignore
    finally:
        if inserted:
            try:
                sys.path.remove(str(steady_root))
            except ValueError:
                pass
    return (
        SteadyUptrendConfig,
        steady_uptrend_signal,
        SteadyHtmlReporter,
        SteadyMarkdownReporter,
        AnalysisResult,
        PipelineResult,
    )


def _import_new_dependencies():
    """临时将 check-new-indicators 加入 sys.path, 导入新指标相关组件."""
    # 清理可能由前两个模块留下的同名顶层包
    for name in [
        "reporters",
        "reporters.html_reporter",
        "reporters.markdown_reporter",
        "data_loader",
        "pipeline",
    ]:
        sys.modules.pop(name, None)
    new_root = BASE_DIR / "check-new-indicators"
    inserted = False
    if str(new_root) not in sys.path:
        sys.path.insert(0, str(new_root))
        inserted = True
    try:
        from analyzer import StockAnalyzer  # type: ignore
        from reporter import Reporter as NewReporter  # type: ignore
    finally:
        if inserted:
            try:
                sys.path.remove(str(new_root))
            except ValueError:
                pass
    return StockAnalyzer, NewReporter


def _analyze_td_single(
    df_daily: pd.DataFrame,
    stock: StockInfo,
    td_analyzer: Any,
) -> Optional[Dict[str, Any]]:
    """使用 TDAnalyzer 核心逻辑分析单只股票, 返回命中结果行."""
    if df_daily is None or df_daily.empty:
        return None

    analysis = td_analyzer._analyze_stock(df_daily)  # 私有方法在此作为内部复用
    level = analysis.get("共振级别", "无底部信号")
    if level == "无底部信号":
        return None

    row: Dict[str, Any] = dict(analysis)
    row["代码"] = stock.code
    row["名称"] = stock.name
    row["板块"] = _get_board_type(stock.code)
    row["行业"] = stock.industry or "未知"
    return row


def _analyze_steady_single(
    df_daily: pd.DataFrame,
    stock: StockInfo,
    steady_config: Any,
    steady_uptrend_signal_fn: Any,
) -> Optional[Dict[str, Any]]:
    """使用稳步上升指标分析单只股票, 仅在命中时返回行."""
    if df_daily is None or df_daily.empty:
        return None

    signal = steady_uptrend_signal_fn(df_daily, steady_config)
    if not signal.get("steady_uptrend"):
        return None

    latest_date = signal.get("latest_date")
    try:
        latest_date_str = (
            pd.Timestamp(latest_date).strftime("%Y-%m-%d") if latest_date else ""
        )
    except Exception:
        latest_date_str = str(latest_date) if latest_date else ""

    row: Dict[str, Any] = {
        "代码": stock.code,
        "名称": stock.name,
        "板块": _get_board_type(stock.code),
        "行业": stock.industry or "未知",
        "latest_date": latest_date_str,
        "latest_close": signal.get("latest_close"),
        "steady_uptrend": bool(signal.get("steady_uptrend")),
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
    # 回调买点 / 等待买点 默认 False, 以便与现有 HtmlReporter 兼容
    row["回调买点"] = False
    row["等待买点"] = False
    return row


def _analyze_new_single(
    df_daily: pd.DataFrame,
    stock: StockInfo,
    stock_analyzer: Any,
) -> Optional[Dict[str, Any]]:
    """使用新指标 StockAnalyzer 分析单只股票."""
    if df_daily is None or df_daily.empty:
        return None
    info = {
        "code": stock.code,
        "name": stock.name,
        "industry": stock.industry or "",
    }
    return stock_analyzer.analyze(df_daily, info)


def _build_td_reports(
    td_results: List[Dict[str, Any]],
    analysis_date: str,
    td_analyzer: Any,
    TDMarkdownReporter: Any,
    TDHTMLReporter: Any,
) -> Optional[Path]:
    """根据 TD 结果生成 CSV + Markdown + HTML, 并写入 stocks_index."""
    if not td_results:
        print("[TD] 当日无九底信号, 跳过 TD 报告生成")
        return None

    df = pd.DataFrame(td_results)

    # 云端轻量专属目录: PlanToDeploy/output/cloud_td
    output_root = CLOUD_BASE / "cloud_td"
    date_dir = output_root / analysis_date
    time_dir = date_dir / datetime.now().strftime("%H-%M-%S")
    time_dir.mkdir(parents=True, exist_ok=True)

    csv_path = td_analyzer.save(df, output_dir=time_dir)

    md_reporter = TDMarkdownReporter(time_dir, end_date=analysis_date)
    md_reporter.generate(df, title="TD九底分析报告")

    html_reporter = TDHTMLReporter(
        time_dir,
        end_date=analysis_date,
        display_date=analysis_date,
    )
    summary_path = html_reporter.generate(df, title="TD九底分析报告")

    print(f"[TD] 已生成 CSV: {csv_path.name}")
    print(f"[TD] 已生成 HTML 报告目录: {summary_path.parent}")
    return summary_path


def _build_steady_reports(
    steady_results: List[Dict[str, Any]],
    analysis_date: str,
    SteadyMarkdownReporter: Any,
    SteadyHtmlReporter: Any,
    AnalysisResult: Any,
    PipelineResult: Any,
) -> Optional[Path]:
    """根据稳步上升命中结果生成 Markdown + HTML + 索引."""
    if not steady_results:
        print("[稳步上升] 当日无信号, 跳过稳步上升报告生成")
        return None

    df = pd.DataFrame(steady_results)

    # 云端轻量专属目录: PlanToDeploy/output/cloud_steady
    output_root = CLOUD_BASE / "cloud_steady"
    date_dir = output_root / analysis_date
    time_dir = date_dir / datetime.now().strftime("%H-%M-%S")
    time_dir.mkdir(parents=True, exist_ok=True)

    analysis = AnalysisResult(
        name="steady_uptrend",
        data=df,
        summary={
            "total": len(df),
            "signal_count": len(df),
        },
    )
    combined = {"稳步上升": df}
    pipe_result = PipelineResult(
        steady_uptrend=analysis,
        combined=combined,
        batch_dir=time_dir,
    )

    md_reporter = SteadyMarkdownReporter(
        result=pipe_result,
        output_dir=time_dir,
        end_date=analysis_date,
    )
    md_reporter.generate()

    html_reporter = SteadyHtmlReporter(
        result=pipe_result,
        output_dir=time_dir,
        end_date=analysis_date,
        display_date=analysis_date,
    )
    html_reporter.generate()

    print(f"[稳步上升] 已生成输出目录: {time_dir}")
    return time_dir


def _build_new_reports(
    new_results: List[Dict[str, Any]],
    analysis_date: str,
    NewReporter: Any,
) -> Optional[Path]:
    """根据新指标结果生成 CSV + Markdown + HTML + 索引."""
    if not new_results:
        print("[新指标] 当日无命中结果, 跳过新指标报告生成")
        return None

    # 云端轻量专属目录: PlanToDeploy/output/cloud_new
    output_root = CLOUD_BASE / "cloud_new"
    output_root.mkdir(parents=True, exist_ok=True)

    reporter = NewReporter(new_results, end_date=analysis_date, base_output_dir=output_root)
    csv_path = reporter.save_csv()
    md_path = reporter.save_markdown()
    html_path = reporter.save_html()

    print(f"[新指标] 已生成 CSV: {csv_path}")
    print(f"[新指标] 已生成 MD: {md_path}")
    print(f"[新指标] 已生成 HTML: {html_path}")
    return html_path


def _build_global_reports_index() -> None:
    """调用 scripts/build_reports_index.py 重建全局报告索引."""
    script_path = BASE_DIR / "scripts" / "build_reports_index.py"
    if not script_path.exists():
        print("[索引] 未找到 scripts/build_reports_index.py, 跳过索引构建")
        return

    try:
        subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
        )
        print("[索引] 已在 report_index/* 下重建 reports_index.html / reports_list.html")
    except Exception as exc:
        print(f"[索引] 构建全局报告索引失败: {exc}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="云端轻量 Runner - 流式执行 TD九底 / 稳步上升 / 新指标",
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
    parser.add_argument(
        "--no-td",
        action="store_true",
        help="跳过 TD 九底模块",
    )
    parser.add_argument(
        "--no-steady",
        action="store_true",
        help="跳过稳步上升模块",
    )
    parser.add_argument(
        "--no-new",
        action="store_true",
        help="跳过新指标模块",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    # 1) 加载股票池
    if args.test and not args.stocks_file:
        selected_path = BASE_DIR / "PlanToDeploy" / "selected_stocks_all copy.csv"
        print(f"[Runner] 测试模式: 使用股票池文件 {selected_path}")
    else:
        selected_path = Path(args.stocks_file) if args.stocks_file else None
    stocks = load_stock_pool_from_selected_all(
        selected_path=selected_path,
        limit=args.limit,
    )
    if not stocks:
        print("[Runner] 股票池为空, 无需执行分析")
        return 0

    print(f"[Runner] 股票池数量: {len(stocks)}")

    # 2) 导入各模块依赖
    TDAnalyzer, TDAnalyzerConfig, TDHTMLReporter, TDMarkdownReporter = _import_td_dependencies()
    (
        SteadyUptrendConfig,
        steady_uptrend_signal,
        SteadyHtmlReporter,
        SteadyMarkdownReporter,
        AnalysisResult,
        PipelineResult,
    ) = _import_steady_dependencies()
    StockAnalyzer, NewReporter = _import_new_dependencies()

    # 3) 初始化分析配置
    td_analyzer = TDAnalyzer(
        TDAnalyzerConfig(
            days=args.days,
            td_threshold=9,
            near_threshold=7,
        ),
        output_dir=BASE_DIR,  # 实际保存目录在 _build_td_reports 中覆盖
    )
    steady_config = SteadyUptrendConfig()

    td_results: List[Dict[str, Any]] = []
    steady_results: List[Dict[str, Any]] = []
    new_results: List[Dict[str, Any]] = []
    global_max_date: Optional[datetime] = None

    # 4) 登录 BaoStock(如可用), 开始流式拉数 + 分析
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

            # TD 九底
            if not args.no_td:
                td_row = _analyze_td_single(df_daily, stock, td_analyzer)
                if td_row is not None:
                    td_results.append(td_row)

            # 稳步上升
            if not args.no_steady:
                steady_row = _analyze_steady_single(
                    df_daily,
                    stock,
                    steady_config,
                    steady_uptrend_signal,
                )
                if steady_row is not None:
                    steady_results.append(steady_row)

            # 新指标
            if not args.no_new:
                new_row = _analyze_new_single(df_daily, stock, StockAnalyzer)
                if new_row is not None:
                    new_results.append(new_row)

            # 用完立即丢弃 df_daily 引用, 降低峰值内存
            del df_daily
    finally:
        logout_baostock()

    # 5) 确定分析日期(优先 end-date, 否则使用全局最新数据日期)
    if args.end_date:
        analysis_date = args.end_date
    elif global_max_date is not None:
        analysis_date = pd.Timestamp(global_max_date).strftime("%Y-%m-%d")
    else:
        analysis_date = datetime.now().strftime("%Y-%m-%d")

    print(f"[Runner] 本次分析日期: {analysis_date}")

    # 6) 各模块生成报告 + stocks_index
    if not args.no_td:
        _build_td_reports(
            td_results,
            analysis_date,
            td_analyzer,
            TDMarkdownReporter,
            TDHTMLReporter,
        )

    if not args.no_steady:
        _build_steady_reports(
            steady_results,
            analysis_date,
            SteadyMarkdownReporter,
            SteadyHtmlReporter,
            AnalysisResult,
            PipelineResult,
        )

    if not args.no_new:
        _build_new_reports(
            new_results,
            analysis_date,
            NewReporter,
        )

    # 7) 重建全局报告索引
    _build_global_reports_index()

    print("[Runner] 云端轻量 Runner 执行完毕")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
