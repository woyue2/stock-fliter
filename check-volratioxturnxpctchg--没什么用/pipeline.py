# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  limit: Optional[int], end_date: Optional[str], auto_open: bool, config_path: str|None
# OUTPUT: Dict — {scanned, matched, files}
# POS:    check-volratioxturnxpctchg/pipeline.py
# -*- coding: utf-8 -*-
"""
Pipeline 模块

调用链:
  main.py → run_pipeline() → data_loader → SurgeAnalyzer → Reporter
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import sys
import webbrowser
from pathlib import Path
from typing import Any, Optional

_ROOT_DIR = Path(__file__).resolve().parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from util.system_utils import get_optimal_worker_count
from data_loader import iter_stock_items, load_daily_data
from analyzers import StockAnalyzer
from reporter import Reporter
from config_loader import load_config

try:
    from util.progress import ProgressBar
except ImportError:
    class ProgressBar:
        def __init__(self, total, desc): self.desc = desc
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def update(self, n=1, **kwargs): pass


def _worker(item: Any, cfg: dict) -> Optional[dict]:
    """子进程：加载 + 分析单只股票"""
    try:
        df = load_daily_data(item.code)
        info = {
            "code": item.code,
            "name": item.name,
            "industry": item.industry,
            "concepts": item.concepts
        }
        return StockAnalyzer.analyze(df, info, cfg)
    except Exception:
        return None


def run_pipeline(
    limit: Optional[int] = None,
    end_date: Optional[str] = None,
    auto_open: bool = True,
    config_path: Optional[str] = None,
) -> dict:
    """运行量比×换手率×涨跌幅全流程"""
    cfg = load_config(config_path)
    print(f"🚀 开始量比×换手率×涨跌幅筛选... [config: {config_path or 'default.json'}]")
    items = list(iter_stock_items(limit=limit))
    print(f"📋 待分析股票数: {len(items)}")

    workers = _decide_workers()
    results = _scan(items, workers, cfg)

    print(f"\n📊 分析完成，命中股票数: {len(results)}")
    files = _report(results, end_date, auto_open)

    return {"scanned": len(items), "matched": len(results), "files": files}


def _decide_workers() -> int:
    """根据内存决定并行度"""
    if os.environ.get("LOW_MEM_MODE") == "1":
        print("  [INFO] 低内存模式：单进程")
        return 1
    w = get_optimal_worker_count()
    label = f"{w} 进程并行" if w > 1 else "单进程"
    print(f"  [INFO] {label}")
    return w


def _scan(items: list, workers: int, cfg: dict) -> list:
    """执行扫描（并行或串行）"""
    if workers > 1:
        return _scan_parallel(items, workers, cfg)
    return _scan_serial(items, cfg)


def _scan_parallel(items: list, workers: int, cfg: dict) -> list:
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_worker, it, cfg): it for it in items}
        with ProgressBar(len(items), desc="并行分析") as pbar:
            for f in as_completed(futures):
                res = f.result()
                if res:
                    results.append(res)
                pbar.update(1, success=bool(res))
    return results


def _scan_serial(items: list, cfg: dict) -> list:
    results = []
    with ProgressBar(len(items), desc="分析") as pbar:
        for item in items:
            res = _worker(item, cfg)
            if res:
                results.append(res)
            pbar.update(1, success=bool(res))
    return results


def _report(results: list, end_date: str | None, auto_open: bool) -> dict:
    """生成报告并返回文件路径"""
    files: dict = {}
    if not results:
        print("⚠️ 未找到符合条件的股票")
        return files

    reporter = Reporter(results, end_date)
    for kind, saver in [("csv", reporter.save_csv),
                        ("markdown", reporter.save_markdown),
                        ("html", reporter.save_html)]:
        path = saver()
        if path:
            files[kind] = str(path)
            print(f"✅ {kind.upper()} 报告: {path}")

    _auto_open_html(files.get("html"), auto_open)
    return files


def _auto_open_html(html_path: str | None, auto_open: bool):
    """尝试在浏览器中打开 HTML 报告"""
    if not html_path or not auto_open:
        return
    url = Path(html_path).as_uri()
    print("  🌐 自动打开浏览器...")
    if not webbrowser.open(url) and os.name == "posix":
        _try_wsl_open(url)


def _try_wsl_open(url: str):
    """WSL 环境下尝试打开浏览器"""
    import subprocess
    for cmd in [["wslview", url], ["powershell.exe", "-c", f'start "{url}"']]:
        try:
            subprocess.run(cmd, check=False, capture_output=True)
            return
        except Exception:
            continue
