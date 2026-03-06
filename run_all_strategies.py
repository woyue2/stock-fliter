# -*- coding: utf-8 -*-
"""
统一调度脚本：一键运行数据更新 + 核心分析模块

默认执行顺序：
1. get-data/services/fetch_daily_snap.py (极速快照)
2. check-td/main.py --skip-fetch
3. check-maxrsix6u1d/main.py
4. check-tdxmacdxvolume/main.py
5. check-volupxyangxshipan/main.py

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

# 导入系统工具
sys.path.append(str(PROJECT_ROOT))
from util.system_utils import is_low_memory





@dataclass
class Step:
    name: str
    command: List[str]
    workdir: Path
    group: str = "analysis"  # get-data / analysis / index
    low_mem_mode: bool = False
    shared_raw_dir: Optional[str] = None


def setup_shared_disk_cache() -> Optional[str]:
    """
    [Legacy] 此功能已由 SQLite 取代。读取 SQLite 数据库在 Linux/MacOS 下性能极佳，
    无需再手动将几千个 CSV 搬运到 /dev/shm。
    """
    return None


def cleanup_shared_disk_cache(cache_dir_str: Optional[str]):
    """
    清理 /dev/shm 中的共享内存缓存文件夹，释放物理内存。
    """
    if not cache_dir_str:
        return
    
    import shutil
    cache_dir = Path(cache_dir_str)
    if cache_dir.exists():
        try:
            shutil.rmtree(cache_dir, ignore_errors=True)
            print(f"🗑️ [I/O 优化] 已清理内存磁盘缓存文件夹，物理内存已完全释放。")
        except:
            pass


def run_step(step: Step, capture: bool = False) -> int:
    """执行单个步骤并打印人类可读日志，并写入 summary 日志。"""
    start = datetime.now()

    if not capture:
        print("\n" + "=" * 60)
        print(f"▶ 开始步骤: {step.name}")
        print("-" * 60)
        print(f"[CMD] {' '.join(step.command)}")
        print(f"[CWD] {step.workdir}")

    env = os.environ.copy()
    if capture:
        env["DISABLE_TQDM"] = "1"
    
    # 传递低内存模式标记
    if getattr(step, "low_mem_mode", False):
        env["LOW_MEM_MODE"] = "1"
    
    if getattr(step, "shared_raw_dir", None):
        env["STOCK_RAW_DIR"] = step.shared_raw_dir

    result = subprocess.run(step.command, cwd=str(step.workdir), env=env, capture_output=capture, text=capture)

    end = datetime.now()
    duration = (end - start).total_seconds()

    if capture:
        print("\n" + "=" * 60)
        print(f"▶ 步骤完成: {step.name} (耗时: {duration:.1f}s)")
        print("-" * 60)
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())

    if result.returncode == 0:
        if not capture:
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
        return run_step(s, capture=True)

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
    skip_td: bool,
    skip_maxrsix6u1d: bool,
    skip_tdxmacdxvolume: bool,
    skip_volupxyangxshipan: bool,
    skip_zhulistrength: bool,
    skip_build_index: bool,
    get_minutes: bool,
    end_date: Optional[str],
    limit: Optional[int],
    low_mem_mode: bool = False,
    shared_raw_dir: Optional[str] = None,
) -> List[Step]:
    """根据参数构建需要执行的步骤列表。"""
    steps: List[Step] = []

    # 是否处于“静默模式”：由 NO_BROWSER 环境变量控制
    browser_silent = os.getenv("NO_BROWSER", "").lower() in {"1", "true", "yes"}

    # 1. 更新数据 (默认极速快照模式，基于 SQLite)
    if not skip_get_data:
        steps.append(
            Step(
                name="[极速版] 更新A股最新快照 (Sina/SQLite)",
                command=[sys.executable, "services/fetch_daily_snap.py"],
                workdir=PROJECT_ROOT / "get-data",
                group="get-data",
                low_mem_mode=low_mem_mode
            )
        )

    # 1.5 更新分钟数据
    if get_minutes:
        steps.append(
            Step(
                name="更新A股分时数据 (get-data/fetch_minute_data.py)",
                command=[sys.executable, "fetchers/fetch_minute_data.py", "--all"],
                workdir=PROJECT_ROOT / "get-data",
                group="get-data",
                low_mem_mode=low_mem_mode
            )
        )

    # 公共 end_date 参数
    end_date_args: List[str] = ["--end-date", end_date] if end_date else []

    # 2. TD分析
    if not skip_td:
        # 在静默模式下附加 --no-open，否则允许自动打开浏览器
        cmd = [sys.executable, "main.py", "--skip-fetch"]
        if browser_silent:
            cmd.append("--no-open")
        cmd.extend(end_date_args)
        if limit:
            cmd.extend(["--limit", str(limit)])
        steps.append(
            Step(
                name="TD分析 (check-td)",
                command=cmd,
                workdir=PROJECT_ROOT / "check-td",
                group="analysis",
                low_mem_mode=low_mem_mode,
                shared_raw_dir=shared_raw_dir
            )
        )

    # 3. MA x RSI x 6U1D 动量分析
    if not skip_maxrsix6u1d:
        cmd = [sys.executable, "main.py", *end_date_args]
        if limit:
            cmd.extend(["--limit", str(limit)])
        steps.append(
            Step(
                name="MAxRSIx6U1D分析 (check-maxrsix6u1d)",
                command=cmd,
                workdir=PROJECT_ROOT / "check-maxrsix6u1d",
                group="analysis",
                low_mem_mode=low_mem_mode,
                shared_raw_dir=shared_raw_dir
            )
        )

    # 4. TD x MACD x Volume 指标组合分析
    if not skip_tdxmacdxvolume:
        cmd = [sys.executable, "main.py", *end_date_args]
        if limit:
            cmd.extend(["--limit", str(limit)])
        steps.append(
            Step(
                name="TDxMACDxVolume分析 (check-tdxmacdxvolume)",
                command=cmd,
                workdir=PROJECT_ROOT / "check-tdxmacdxvolume",
                group="analysis",
                low_mem_mode=low_mem_mode,
                shared_raw_dir=shared_raw_dir
            )
        )


    # 4.5 VolUp x Yang x Shipan 动量分析
    if not skip_volupxyangxshipan:
        cmd = [sys.executable, "main.py", *end_date_args]
        if limit:
            cmd.extend(["--limit", str(limit)])
        if browser_silent:
            cmd.append("--no-open")
        steps.append(
            Step(
                name="VolUp x Yang x Shipan 分析 (check-volupxyangxshipan)",
                command=cmd,
                workdir=PROJECT_ROOT / "check-volupxyangxshipan",
                group="analysis",
                low_mem_mode=low_mem_mode,
                shared_raw_dir=shared_raw_dir
            )
        )
    
    # 4.7 主力强度与散户博弈分析 (A*B*C)
    if not skip_zhulistrength:
        cmd = [sys.executable, "main.py"]
        steps.append(
            Step(
                name="主力强度分析 (check-zhulistrength)",
                command=cmd,
                workdir=PROJECT_ROOT / "check-zhulistrength",
                group="analysis",
                low_mem_mode=low_mem_mode
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
                low_mem_mode=low_mem_mode,
                shared_raw_dir=shared_raw_dir
            )
        )

    return steps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="统一运行 get-data + 各分析模块的调度脚本",
        epilog=(
            "默认顺序: get-data → TD分析 → MAxRSIx6U1D → 指标组合 → VolUp x Yang x Shipan\n"
            "示例:\n"
            "  python run_all_strategies.py                 # 全量运行\n"
            "  python run_all_strategies.py --skip-get-data # 仅重新跑分析模块\n"
            "  python run_all_strategies.py --end-date 2026-01-30\n"
        ),
    )
    parser.add_argument(
        "--skip-get-data",
        action="store_true",
        help="跳过日线数据拉取 (get-data/services/fetch_daily_snap.py)",
    )
    parser.add_argument(
        "--use-history",
        action="store_true",
        help="使用慢速历史同步模式 (services/fetch_daily_history.py)，不推荐每日使用",
    )
    parser.add_argument(
        "--get-minutes",
        action="store_true",
        help="执行分钟数据拉取 (get-data/fetch_minute_data.py)，默认跳过",
    )
    parser.add_argument(
        "--skip-td",
        action="store_true",
        help="跳过 TD模块 (check-td)",
    )
    parser.add_argument(
        "--skip-maxrsix6u1d",
        action="store_true",
        help="跳过 MAxRSIx6U1D 模块 (check-maxrsix6u1d)",
    )
    parser.add_argument(
        "--skip-tdxmacdxvolume",
        action="store_true",
        help="跳过 TDxMACDxVolume 模块 (check-tdxmacdxvolume)",
    )
    parser.add_argument(
        "--skip-volupxyangxshipan",
        action="store_true",
        help="跳过 VolUp x Yang x Shipan 模块 (check-volupxyangxshipan)",
    )
    parser.add_argument(
        "--skip-zhulistrength",
        action="store_true",
        help="跳过主力强度分析模块 (check-zhulistrength)",
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
    parser.add_argument(
        "--no-server-optimization",
        action="store_true",
        help="不使用服务器级多进程扫描优化（适合 2G 及以下内存服务器）",
    )
    return parser.parse_args()


def interactive_prompt(args: argparse.Namespace) -> None:
    """交互式终端：无参数时触发，动态调整 args 的 boolean flag"""
    print("=" * 40)
    print("🚀 股票分析综合调度系统启动")
    print("=" * 40)

    # 1. 数据配置问询
    print("\n[步骤 1] 是否执行日线数据快照更新 (get-data/services/fetch_daily_snap.py)?")
    print("[1] 是 (极速快照模式，推荐)")
    print("[H] 补全历史 (fetch_daily_history.py)")
    print("[0] 跳过，使用已有数据 (默认)")
    ans_data = input("👉 请选择 [1/H/0, 默认0]: ").strip().upper()
    if ans_data == "1":
        args.skip_get_data = False
        args.use_history = False
    elif ans_data == "H":
        args.skip_get_data = False
        args.use_history = True
    else:
        args.skip_get_data = True

    # 1.5 分钟数据配置问询
    print("\n[步骤 1.5] 是否执行分钟数据爬取 (get-data/fetch_minute_data.py)?")
    print("[1] 是")
    print("[0] 跳过 (默认)")
    ans_min = input("👉 请选择 [1/0, 默认0]: ").strip()
    if ans_min == "1":
        args.get_minutes = True

    # 2. 策略模块问询
    print("\n[配置] 是否开启服务器级优化 (多进程并发扫描)?")
    if is_low_memory():
        print("  ⚠️ 检测到当前系统内存不足 2.5G，建议跳过多进程以保证稳定性。")
        ans_opt = input("👉 开启多进程? [1/0, 默认0]: ").strip()
        if ans_opt != "1":
            args.no_server_optimization = True
    else:
        print("  🚀 系统内存充足，默认开启多进程加速。")
        ans_opt = input("👉 关闭多进程? [1/0, 默认0]: ").strip()
        if ans_opt == "1":
            args.no_server_optimization = True

    print("\n[步骤 2] 分析环境配置完成。以下是可用的策略模块：")
    print("[1] TD分析 (check-td)")
    print("[2] MAxRSIx6U1D 分析 (check-maxrsix6u1d)")
    print("[3] TDxMACDxVolume 分析 (check-tdxmacdxvolume)")
    print("[4] VolUp x Yang x Shipan 分析 (check-volupxyangxshipan)")
    print("[5] 主力强度 A*B*C 分析 (check-zhulistrength)")
    print("\n有不需要执行的模组吗？(默认全跑，多线程并行)")
    ans_skip = input("👉 请输入要【跳过】的序号组合（比如 '23' 跳过稳步和组合，直接回车代表全跑）: ").strip()
    
    if "1" in ans_skip: args.skip_td = True
    if "2" in ans_skip: args.skip_maxrsix6u1d = True
    if "3" in ans_skip: args.skip_tdxmacdxvolume = True
    if "4" in ans_skip: args.skip_volupxyangxshipan = True
    if "5" in ans_skip: args.skip_zhulistrength = True

    # 3. 执行模式问询
    print("\n[步骤 3] 执行模式：是否开启【模块间】并行运行?")
    print("  (注：同时启动 TD、6U1D、组合、VolUp 等模块，节省总耗时)")
    print("[1] 并行运行 (默认)")
    print("[0] 顺序运行 (更稳定的日志流)")
    ans_par = input("👉 请选择 [1/0, 默认1]: ").strip()
    if ans_par == "0":
        args.parallel = False
    else:
        args.parallel = True

    print("\n[开始执行...]")


def main() -> int:
    args = parse_args()

    # 如果没有指定任何跳过参数，且在交互式终端下，进入向导流程
    is_explicit = any([
        args.skip_get_data, args.skip_td, args.skip_maxrsix6u1d, 
        args.skip_tdxmacdxvolume, args.skip_volupxyangxshipan,
        args.skip_zhulistrength,
        args.get_minutes
    ])
    if not is_explicit and sys.stdin.isatty():
        interactive_prompt(args)

    # I/O 优化：如果内存充足，设置共享 RAM 磁盘缓存
    shared_raw_dir = None
    if not args.no_server_optimization:
        shared_raw_dir = setup_shared_disk_cache()

    steps = build_steps(
        skip_get_data=args.skip_get_data,
        skip_td=args.skip_td,
        skip_maxrsix6u1d=args.skip_maxrsix6u1d,
        skip_tdxmacdxvolume=args.skip_tdxmacdxvolume,
        skip_volupxyangxshipan=args.skip_volupxyangxshipan,
        skip_zhulistrength=args.skip_zhulistrength,
        skip_build_index=args.skip_build_index,
        get_minutes=args.get_minutes,
        end_date=args.end_date,
        limit=args.limit,
        low_mem_mode=args.no_server_optimization or is_low_memory(),
        shared_raw_dir=None # 彻底废弃 CSV 预载模式
    )

    if args.use_history and not args.skip_get_data:
        for s in steps:
            if s.group == "get-data" and "fetch_daily_snap.py" in str(s.command):
                s.name = "[完整版] 补全A股历史日K (BaoStock/SQLite)"
                s.command = [sys.executable, "services/fetch_daily_history.py", "--all"]

    if not steps:
        print("⚠️ 未选择任何要执行的步骤，请检查参数。")
        return 1

    print("=" * 60)
    print("🚀 统一调度开始")
    print("=" * 60)

    try:
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
    finally:
        # 释放内存磁盘
        cleanup_shared_disk_cache(shared_raw_dir)


if __name__ == "__main__":
    raise SystemExit(main())
