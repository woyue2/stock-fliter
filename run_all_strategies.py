# -*- coding: utf-8 -*-
"""
统一调度脚本：一键运行数据更新 + 核心分析模块

默认执行顺序：
1. get-data/main.py --all
2. check-trend-bottom/main.py --skip-fetch
3. check-steady-uptrend/main.py
4. check-indicator-combo/main.py
5. check-volume-confirmation/main.py

设计目标：
- 便于在本地或云端用单个入口脚本挂到定时任务
- 不改动各子模块的内部实现和输出路径
"""
from __future__ import annotations

import os
import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass
class Step:
    name: str
    command: List[str]
    workdir: Path
    group: str = "analysis"  # get-data / analysis / index


def run_step(step: Step) -> int:
    """执行单个步骤并打印人类可读日志，并写入 summary 日志。"""
    start = datetime.now()

    print("\n" + "=" * 60)
    print(f"▶ 开始步骤: {step.name}")
    print("-" * 60)
    print(f"[CMD] {' '.join(step.command)}")
    print(f"[CWD] {step.workdir}")

    env = os.environ.copy()

    result = subprocess.run(step.command, cwd=str(step.workdir), env=env)

    end = datetime.now()
    duration = (end - start).total_seconds()

    if result.returncode == 0:
        print(f"\n✅ 步骤完成: {step.name}")
    else:
        print(f"\n❌ 步骤失败: {step.name} (exit={result.returncode})")

    # 写入 summary 日志
    try:
        log_dir = PROJECT_ROOT / "logs" / "run_all"
        log_dir.mkdir(parents=True, exist_ok=True)
        summary_path = log_dir / "summary.log"
        with summary_path.open("a", encoding="utf-8") as f:
            f.write(
                f"[{start.strftime('%Y-%m-%d %H:%M:%S')}] START {step.name} "
                f"group={step.group} cmd=\"{' '.join(step.command)}\"\n"
            )
            f.write(
                f"[{end.strftime('%Y-%m-%d %H:%M:%S')}] END   {step.name} "
                f"code={result.returncode} duration={duration:.1f}s\n"
            )
    except Exception:
        # 日志失败不影响主流程
        pass

    return result.returncode


def run_steps_sequential(steps: List[Step], ignore_errors: bool) -> int:
    for step in steps:
        exit_code = run_step(step)
        if exit_code != 0 and not ignore_errors:
            print("\n⛔ 检测到错误，已停止后续步骤。")
            return exit_code
    return 0


def run_steps_parallel(steps: List[Step], ignore_errors: bool) -> int:
    """并行运行一组步骤（典型用在多个分析模块之间）。"""
    if not steps:
        return 0

    print("\n" + "=" * 60)
    print("⚙️ 并行运行分析模块:")
    for s in steps:
        print(f"  - {s.name}")
    print("=" * 60)

    exit_codes: List[int] = []

    def _run(s: Step) -> int:
        return run_step(s)

    with ThreadPoolExecutor(max_workers=len(steps)) as executor:
        future_map = {executor.submit(_run, s): s for s in steps}
        for future in as_completed(future_map):
            code = future.result()
            exit_codes.append(code)

    failed_codes = [c for c in exit_codes if c != 0]
    if failed_codes and not ignore_errors:
        print("\n⛔ 检测到并行步骤中的错误，退出码: ", failed_codes)
        return failed_codes[0]

    return 0


def build_steps(
    skip_get_data: bool,
    skip_trend_bottom: bool,
    skip_steady_uptrend: bool,
    skip_indicator_combo: bool,
    skip_volume_confirmation: bool,
    skip_build_index: bool,
    get_minutes: bool,
    end_date: Optional[str],
    limit: Optional[int],
) -> List[Step]:
    """根据参数构建需要执行的步骤列表。"""
    steps: List[Step] = []

    # 是否处于“静默模式”：由 NO_BROWSER 环境变量控制
    browser_silent = os.getenv("NO_BROWSER", "").lower() in {"1", "true", "yes"}

    # 1. 更新数据
    if not skip_get_data:
        steps.append(
            Step(
                name="更新A股日K数据 (get-data)",
                command=[sys.executable, "main.py"],
                workdir=PROJECT_ROOT / "get-data",
                group="get-data",
            )
        )

    # 1.5 更新分钟数据
    if get_minutes:
        steps.append(
            Step(
                name="更新A股分钟数据 (get-data/fetch_minute_data.py)",
                command=[sys.executable, "fetch_minute_data.py", "--all"],
                workdir=PROJECT_ROOT / "get-data",
                group="get-data",
            )
        )

    # 公共 end_date 参数
    end_date_args: List[str] = ["--end-date", end_date] if end_date else []

    # 2. TD九底分析
    if not skip_trend_bottom:
        # 在静默模式下附加 --no-open，否则允许自动打开浏览器
        cmd = [sys.executable, "main.py", "--skip-fetch"]
        if browser_silent:
            cmd.append("--no-open")
        cmd.extend(end_date_args)
        if limit:
            cmd.extend(["--limit", str(limit)])
        steps.append(
            Step(
                name="TD九底分析 (check-trend-bottom)",
                command=cmd,
                workdir=PROJECT_ROOT / "check-trend-bottom",
                group="analysis",
            )
        )

    # 3. 稳步上升 / 趋势分析
    if not skip_steady_uptrend:
        # 使用完整流程（读取 get-data/raw 数据并重新分析），不再复用旧结果，
        # 便于在自动化/定时任务中每次得到新的稳步上升扫描结果。
        cmd = [sys.executable, "main.py", *end_date_args]
        if limit:
            cmd.extend(["--limit", str(limit)])
        steps.append(
            Step(
                name="稳步上升分析 (check-steady-uptrend)",
                command=cmd,
                workdir=PROJECT_ROOT / "check-steady-uptrend",
                group="analysis",
            )
        )

    # 4. 指标组合分析
    if not skip_indicator_combo:
        cmd = [sys.executable, "main.py", *end_date_args]
        if limit:
            cmd.extend(["--limit", str(limit)])
        steps.append(
            Step(
                name="指标组合分析 (check-indicator-combo)",
                command=cmd,
                workdir=PROJECT_ROOT / "check-indicator-combo",
                group="analysis",
            )
        )


    # 4.5 量价确认分析
    if not skip_volume_confirmation:
        cmd = [sys.executable, "main.py", *end_date_args]
        if limit:
            cmd.extend(["--limit", str(limit)])
        if browser_silent:
            cmd.append("--no-open")
        steps.append(
            Step(
                name="量价确认分析 (check-volume-confirmation)",
                command=cmd,
                workdir=PROJECT_ROOT / "check-volume-confirmation",
                group="analysis",
            )
        )

    # 5. 生成报告索引（reports_list.html 等）
    if not skip_build_index:
        steps.append(
            Step(
                name="生成报告索引 (scripts/build_reports_index.py)",
                command=[sys.executable, "build_reports_index.py"],
                workdir=PROJECT_ROOT / "scripts",
                group="index",
            )
        )

    return steps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="统一运行 get-data + 各分析模块的调度脚本",
        epilog=(
            "默认顺序: get-data → TD九底 → 稳步上升 → 指标组合 → 量价确认\n"
            "示例:\n"
            "  python run_all_strategies.py                 # 全量运行\n"
            "  python run_all_strategies.py --skip-get-data # 仅重新跑分析模块\n"
            "  python run_all_strategies.py --end-date 2026-01-30\n"
        ),
    )
    parser.add_argument(
        "--skip-get-data",
        action="store_true",
        help="跳过日线数据拉取 (get-data/main.py)",
    )
    parser.add_argument(
        "--get-minutes",
        action="store_true",
        help="执行分钟数据拉取 (get-data/fetch_minute_data.py)，默认跳过",
    )
    parser.add_argument(
        "--skip-trend-bottom",
        action="store_true",
        help="跳过 TD九底模块 (check-trend-bottom)",
    )
    parser.add_argument(
        "--skip-steady-uptrend",
        action="store_true",
        help="跳过 稳步上升模块 (check-steady-uptrend)",
    )
    parser.add_argument(
        "--skip-indicator-combo",
        action="store_true",
        help="跳过 指标组合模块 (check-indicator-combo)",
    )
    parser.add_argument(
        "--skip-volume-confirmation",
        action="store_true",
        help="跳过 量价确认模块 (check-volume-confirmation)",
    )
    parser.add_argument(
        "--skip-build-index",
        action="store_true",
        help="跳过生成报告索引 (scripts/build_reports_index.py)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="分析截止日期 (YYYY-MM-DD)，会传递给支持该参数的模块",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制分析股票数量",
    )
    parser.add_argument(
        "--ignore-errors",
        action="store_true",
        help="某一步失败时继续执行后续步骤（默认遇错即停止）",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="并行运行各分析模块（get-data 与索引仍顺序执行）",
    )
    return parser.parse_args()


def interactive_prompt(args: argparse.Namespace) -> None:
    """交互式终端：无参数时触发，动态调整 args 的 boolean flag"""
    print("=" * 40)
    print("🚀 股票分析综合调度系统启动")
    print("=" * 40)

    # 1. 数据配置问询
    print("\n[步骤 1] 是否执行日线数据爬取与更新 (get-data/main.py)?")
    print("[1] 是")
    print("[0] 跳过，使用已有数据 (默认)")
    ans_data = input("👉 请选择 [1/0, 默认0]: ").strip()
    if ans_data != "1":
        args.skip_get_data = True

    # 1.5 分钟数据配置问询
    print("\n[步骤 1.5] 是否执行分钟数据爬取 (get-data/fetch_minute_data.py)?")
    print("[1] 是")
    print("[0] 跳过 (默认)")
    ans_min = input("👉 请选择 [1/0, 默认0]: ").strip()
    if ans_min == "1":
        args.get_minutes = True

    # 2. 策略模块问询
    print("\n[步骤 2] 分析环境配置完成。以下是可用的策略模块：")
    print("[1] TD九底分析 (check-trend-bottom)")
    print("[2] 稳步上升分析 (check-steady-uptrend)")
    print("[3] 指标组合分析 (check-indicator-combo)")
    print("[4] 量价确认分析 (check-volume-confirmation)")
    print("\n有不需要执行的模组吗？(默认全跑，多线程并行)")
    ans_skip = input("👉 请输入要【跳过】的序号组合（比如 '23' 跳过稳步和组合，直接回车代表全跑）: ").strip()
    
    if "1" in ans_skip: args.skip_trend_bottom = True
    if "2" in ans_skip: args.skip_steady_uptrend = True
    if "3" in ans_skip: args.skip_indicator_combo = True
    if "4" in ans_skip: args.skip_volume_confirmation = True

    # 交互模式下默认开启多线程
    args.parallel = True
    print("\n[开始执行...]")


def main() -> int:
    args = parse_args()

    # 如果没有任何参数，则触发交互式向导
    if len(sys.argv) == 1 and sys.stdin.isatty():
        interactive_prompt(args)

    steps = build_steps(
        skip_get_data=args.skip_get_data,
        skip_trend_bottom=args.skip_trend_bottom,
        skip_steady_uptrend=args.skip_steady_uptrend,
        skip_indicator_combo=args.skip_indicator_combo,
        skip_volume_confirmation=args.skip_volume_confirmation,
        skip_build_index=args.skip_build_index,
        get_minutes=args.get_minutes,
        end_date=args.end_date,
        limit=args.limit,
    )

    if not steps:
        print("⚠️ 未选择任何要执行的步骤，请检查参数。")
        return 1

    print("=" * 60)
    print("🚀 统一调度开始")
    print("=" * 60)

    if args.parallel:
        # 分阶段执行：先 get-data，再并行 analysis，最后 index
        pre_steps = [s for s in steps if s.group == "get-data"]
        analysis_steps = [s for s in steps if s.group == "analysis"]
        post_steps = [s for s in steps if s.group == "index"]

        code = run_steps_sequential(pre_steps, ignore_errors=args.ignore_errors)
        if code != 0 and not args.ignore_errors:
            return code

        code = run_steps_parallel(analysis_steps, ignore_errors=args.ignore_errors)
        if code != 0 and not args.ignore_errors:
            return code

        code = run_steps_sequential(post_steps, ignore_errors=args.ignore_errors)
        if code != 0 and not args.ignore_errors:
            return code
    else:
        code = run_steps_sequential(steps, ignore_errors=args.ignore_errors)
        if code != 0:
            return code

    print("\n" + "=" * 60)
    print("✅ 所有步骤执行完成")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
