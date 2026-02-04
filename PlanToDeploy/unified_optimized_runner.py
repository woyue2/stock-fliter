# -*- coding: utf-8 -*-
"""
统一优化 Runner - 读一次数据，运行三个完整模块

包含：
1. TD九底 (完整)
2. 新指标 (完整)
3. 玄学组合 (完整 Pipeline)
   - 稳步上升(完整版)
   - 趋势分析
   - 网格测试
   - 玄学指标组合

核心优化：
- 只读一次股票池
- 每只股票只获取一次数据
- TD九底 + 新指标在数据读取时同步分析
- 所有数据收集完后，运行玄学组合 Pipeline
- 保持各模块原有报告格式不变
"""
from __future__ import annotations

import argparse
import shutil
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
CLOUD_BASE = BASE_DIR / "output"


def _get_board_type(code: str) -> str:
    """根据股票代码判断所属交易板块"""
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


# ============================================================================
# 导入所有分析器组件（复用 stream_run_daily.py）
# ============================================================================

def _import_td_dependencies():
    """导入 TD九底组件"""
    td_root = BASE_DIR / "check-trend-bottom"
    if str(td_root) not in sys.path:
        sys.path.insert(0, str(td_root))
    try:
        from analyzers.td_analyzer import TDAnalyzer, TDAnalyzerConfig
        from reporters.html_reporter import HTMLReporter as TDHTMLReporter
        from reporters.markdown_reporter import MarkdownReporter as TDMarkdownReporter
    finally:
        if str(td_root) in sys.path:
            try:
                sys.path.remove(str(td_root))
            except ValueError:
                pass
    return TDAnalyzer, TDAnalyzerConfig, TDHTMLReporter, TDMarkdownReporter


def _import_new_dependencies():
    """导入新指标组件"""
    for name in ["analyzer", "reporter", "data_loader"]:
        sys.modules.pop(name, None)

    new_root = BASE_DIR / "check-new-indicators"
    if str(new_root) not in sys.path:
        sys.path.insert(0, str(new_root))
    try:
        from analyzer import StockAnalyzer
        from reporter import Reporter as NewReporter
    finally:
        if str(new_root) in sys.path:
            try:
                sys.path.remove(str(new_root))
            except ValueError:
                pass
    return StockAnalyzer, NewReporter


# 从 stream_run_daily.py 复用的分析函数
def _analyze_td_single(
    df_daily: pd.DataFrame,
    stock: StockInfo,
    td_analyzer: Any,
) -> Optional[Dict[str, Any]]:
    """使用 TDAnalyzer 核心逻辑分析单只股票"""
    if df_daily is None or df_daily.empty:
        return None

    analysis = td_analyzer._analyze_stock(df_daily)
    level = analysis.get("共振级别", "无底部信号")
    if level == "无底部信号":
        return None

    row: Dict[str, Any] = dict(analysis)
    row["代码"] = stock.code
    row["名称"] = stock.name
    row["板块"] = _get_board_type(stock.code)
    row["行业"] = stock.industry or "未知"
    return row


def _analyze_new_single(
    df_daily: pd.DataFrame,
    stock: StockInfo,
    stock_analyzer: Any,
) -> Optional[Dict[str, Any]]:
    """使用新指标 StockAnalyzer 分析单只股票"""
    if df_daily is None or df_daily.empty:
        return None
    info = {
        "code": stock.code,
        "name": stock.name,
        "industry": stock.industry or "",
    }
    return stock_analyzer.analyze(df_daily, info)


# 从 stream_run_daily.py 复用的报告生成函数
def _build_td_reports(
    td_results: List[Dict[str, Any]],
    analysis_date: str,
    td_analyzer: Any,
    TDMarkdownReporter: Any,
    TDHTMLReporter: Any,
) -> Optional[Path]:
    """生成 TD九底报告"""
    if not td_results:
        print("[TD九底] 当日无九底信号, 跳过 TD 报告生成")
        return None

    df = pd.DataFrame(td_results)

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

    print(f"[TD九底] 已生成 CSV: {csv_path.name}")
    print(f"[TD九底] 已生成 HTML 报告目录: {summary_path.parent}")
    return summary_path


def _build_new_reports(
    new_results: List[Dict[str, Any]],
    analysis_date: str,
    NewReporter: Any,
) -> Optional[Path]:
    """生成新指标报告"""
    if not new_results:
        print("[新指标] 当日无命中结果, 跳过新指标报告生成")
        return None

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


# ============================================================================
# 玄学组合 Pipeline（复用 cloud_xuanxue_stream_runner.py 的逻辑）
# ============================================================================

def _run_xuanxue_pipeline(
    stocks_data: Dict[str, pd.DataFrame],
    stocks: List[StockInfo],
    args: argparse.Namespace,
) -> Optional[Path]:
    """
    运行玄学组合 Pipeline（使用已获取的数据）

    完全复用 cloud_xuanxue_stream_runner.py 的逻辑，但使用已获取的数据
    """
    if not stocks_data:
        print("[玄学组合] 无有效数据，跳过")
        return None

    print("\n" + "=" * 60)
    print("📊 运行玄学组合 Pipeline（使用已获取的数据）")
    print("=" * 60)

    # 1. 创建临时 raw 目录，保存已获取的数据
    temp_raw_dir = BASE_DIR / "temp_raw_for_xuanxue"
    temp_raw_dir.mkdir(parents=True, exist_ok=True)

    for code, df in stocks_data.items():
        if df is not None and not df.empty:
            df.to_csv(temp_raw_dir / f"{code}.csv", index=False)

    print(f"[玄学组合] 已保存 {len(stocks_data)} 只股票数据到临时目录")

    # 2. Monkey-patch data_loader（完全复用 cloud_xuanxue_stream_runner.py 的逻辑）
    steady_root = BASE_DIR / "check-steady-uptrend"
    if str(steady_root) not in sys.path:
        sys.path.insert(0, str(steady_root))

    import data_loader as steady_data_loader
    from data_loader import StockItem

    original_iter = steady_data_loader.iter_stock_items
    original_load = steady_data_loader.load_daily_data

    # 创建股票列表
    stock_items = []
    for stock in stocks:
        if stock.code in stocks_data:
            stock_items.append(StockItem(
                code=stock.code,
                name=stock.name,
                bs_code=stock.bs_code,
                industry=stock.industry,
            ))

    # 创建 iter_stock_items 的替代函数
    def iter_stock_items_temp(limit: int | None = None):
        if limit:
            return iter(stock_items[:limit])
        return iter(stock_items)

    # 创建 load_daily_data 的替代函数
    def load_daily_data_temp(code: str, days: int = 365) -> pd.DataFrame:
        code6 = str(code).zfill(6)
        return stocks_data.get(code6, pd.DataFrame())

    # 应用 monkey-patch
    steady_data_loader.iter_stock_items = iter_stock_items_temp
    steady_data_loader.load_daily_data = load_daily_data_temp

    try:
        # 3. 导入并运行 Pipeline（完全复用 cloud_xuanxue_stream_runner.py）
        from pipeline import Pipeline, PipelineConfig

        output_dir = CLOUD_BASE / "cloud_xuanxue"
        output_dir.mkdir(parents=True, exist_ok=True)

        config = PipelineConfig(
            use_steady_uptrend=True,
            use_trend_analysis=True,
            use_grid_test=True,
            use_mystic=True,
            grid_horizon=args.grid_horizon,
            lookback_days=120,
            min_bars=120,
            limit=args.limit,
            output_dir=output_dir,
            end_date=args.end_date,
        )

        pipeline = Pipeline(config)

        # 运行完整流程
        ret = pipeline.run_full()

        # 找到生成的 summary HTML
        batch_dir = pipeline.result.batch_dir
        if isinstance(batch_dir, Path):
            summary_files = sorted(batch_dir.glob("summary_*.html"), reverse=True)
            if summary_files:
                summary_path = summary_files[0]
                print(f"[玄学组合] 已生成报告: {batch_dir}")
                return summary_path

        print(f"[玄学组合] 输出目录: {batch_dir}")
        return batch_dir

    except Exception as e:
        print(f"[玄学组合] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        # 恢复原始函数
        steady_data_loader.iter_stock_items = original_iter
        steady_data_loader.load_daily_data = original_load

        # 清理临时文件
        shutil.rmtree(temp_raw_dir, ignore_errors=True)
        print("[玄学组合] 已清理临时数据")


def _build_global_reports_index() -> None:
    """调用 scripts/build_reports_index.py 重建全局报告索引"""
    script_path = BASE_DIR / "scripts" / "build_reports_index.py"
    if not script_path.exists():
        print("[索引] 未找到 scripts/build_reports_index.py, 跳过索引构建")
        return

    try:
        import subprocess
        subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
        )
        print("[索引] 已在 report_index/* 下重建 reports_index.html / reports_list.html")
    except Exception as exc:
        print(f"[索引] 构建全局报告索引失败: {exc}")


# ============================================================================
# 主流程
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="统一优化 Runner - 读一次数据，运行 TD九底 + 新指标 + 玄学组合",
    )
    parser.add_argument("--end-date", type=str, default=None, help="分析截止日期 (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=365, help="回看天数窗口(默认 365 天)")
    parser.add_argument("--limit", type=int, default=None, help="限制股票池数量")
    parser.add_argument("--test", action="store_true", help="测试模式")
    parser.add_argument("--stocks-file", type=str, default=None, help="自定义股票池文件")
    parser.add_argument("--grid-horizon", type=int, default=20, help="网格测试收益周期(默认20)")
    parser.add_argument("--no-td", action="store_true", help="跳过 TD 九底模块")
    parser.add_argument("--no-new", action="store_true", help="跳过新指标模块")
    parser.add_argument("--no-xuanxue", action="store_true", help="跳过玄学组合模块")
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 60)
    print("🚀 统一优化 Runner")
    print("   读一次数据，运行 TD九底 + 新指标 + 玄学组合")
    print("=" * 60)

    # 1. 加载股票池
    if args.test and not args.stocks_file:
        selected_path = BASE_DIR / "selected_stocks_all copy.csv"
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

    # 2. 导入分析器
    TDAnalyzer, TDAnalyzerConfig, TDHTMLReporter, TDMarkdownReporter = _import_td_dependencies()
    StockAnalyzer, NewReporter = _import_new_dependencies()

    # 3. 初始化分析配置
    if not args.no_td:
        td_analyzer = TDAnalyzer(
            TDAnalyzerConfig(
                days=args.days,
                td_threshold=9,
                near_threshold=7,
            ),
            output_dir=BASE_DIR,
        )

    td_results: List[Dict[str, Any]] = []
    new_results: List[Dict[str, Any]] = []
    stocks_data: Dict[str, pd.DataFrame] = {}  # 保存所有数据供玄学组合使用
    global_max_date: Optional[datetime] = None

    # 4. 开始分析：读一次数据，运行 TD九底 + 新指标
    print("\n" + "=" * 60)
    print("📊 开始分析（读一次数据，运行 TD九底 + 新指标）")
    print("=" * 60)

    login_baostock()
    try:
        for idx, stock in enumerate(stocks, 1):
            # 进度日志：首只 + 每 10 只 + 最后一只
            if idx == 1 or idx % 10 == 0 or idx == len(stocks):
                print(f"[Runner] 进度 {idx}/{len(stocks)} - {stock.code} {stock.name}")

            # 读一次数据
            df_daily = fetch_daily_data_streaming(
                code=stock.code,
                bs_code=stock.bs_code,
                days=args.days,
                end_date=args.end_date,
            )

            if df_daily is None or df_daily.empty:
                if idx == 1 or idx % 10 == 0 or idx == len(stocks):
                    print(f"[Runner] {stock.code} 无有效日线数据, 跳过")
                continue

            # 保存数据供玄学组合使用
            stocks_data[stock.code] = df_daily.copy()

            # 更新全局最新日期
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

            # 新指标
            if not args.no_new:
                new_row = _analyze_new_single(df_daily, stock, StockAnalyzer)
                if new_row is not None:
                    new_results.append(new_row)

            # 进度输出
            signals = []
            if not args.no_td and td_row is not None:
                signals.append("TD")
            if not args.no_new and new_row is not None:
                signals.append("新指标")
            if signals and (idx == 1 or idx % 10 == 0 or idx == len(stocks)):
                print(f"[Runner]   └─ 信号: {' + '.join(signals)}")

            # 用完立即释放内存
            del df_daily

    finally:
        logout_baostock()

    # 5. 确定分析日期
    if args.end_date:
        analysis_date = args.end_date
    elif global_max_date is not None:
        analysis_date = pd.Timestamp(global_max_date).strftime("%Y-%m-%d")
    else:
        analysis_date = datetime.now().strftime("%Y-%m-%d")

    print(f"\n[Runner] 本次分析日期: {analysis_date}")
    print(f"[Runner] 有效数据股票数: {len(stocks_data)}")

    # 6. 生成 TD九底、新指标报告
    print("\n" + "=" * 60)
    print("📊 生成报告...")
    print("=" * 60)

    if not args.no_td:
        _build_td_reports(
            td_results,
            analysis_date,
            td_analyzer,
            TDMarkdownReporter,
            TDHTMLReporter,
        )

    if not args.no_new:
        _build_new_reports(new_results, analysis_date, NewReporter)

    # 7. 运行玄学组合 Pipeline（使用已获取的数据）
    if not args.no_xuanxue:
        _run_xuanxue_pipeline(stocks_data, stocks, args)

    # 8. 重建全局报告索引
    _build_global_reports_index()

    # 9. 打印摘要
    print("\n" + "=" * 60)
    print("📊 分析完成")
    print("=" * 60)
    print(f"分析日期: {analysis_date}")
    print(f"分析股票数: {len(stocks)}")
    print(f"有效数据数: {len(stocks_data)}")
    print(f"\n信号统计:")
    if not args.no_td:
        print(f"  🔴 TD九底:     {len(td_results)} 只")
    if not args.no_new:
        print(f"  🔵 新指标:     {len(new_results)} 只")
    if not args.no_xuanxue:
        print(f"  🎯 玄学组合:   完整 Pipeline（稳步上升 + 趋势 + 网格）")

    print("\n✅ 完成！")
    print("\n说明:")
    print("  - TD九底、新指标：在数据读取时同步分析")
    print("  - 玄学组合：收集完所有数据后，运行完整 Pipeline")
    print("  - 总数据读取次数：1 次")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        raise SystemExit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)
