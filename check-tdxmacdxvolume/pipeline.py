# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  limit: Optional[int], end_date: Optional[str], auto_open: bool
# OUTPUT: Dict — {scanned, matched, files}
# POS:    check-tdxmacdxvolume/pipeline.py（Phase 3 新建，包装 main.py 流程）
# -*- coding: utf-8 -*-
"""
Pipeline 模块

包装现有的数据加载 → 分析 → 报告流程，与其他 check-* 模块保持架构一致。

调用链:
  main.py → run_pipeline() → data_loader → analyzers.StockAnalyzer → reporter.Reporter
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import sys
import webbrowser
from pathlib import Path
from typing import Any, Optional

# 导入系统工具
_ROOT_DIR = Path(__file__).resolve().parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))
from util.system_utils import get_optimal_worker_count
from data_loader import iter_stock_items, load_daily_data
from analyzers import StockAnalyzer
from reporter import Reporter

try:
    from util.progress import ProgressBar
except ImportError:
    class ProgressBar:
        def __init__(self, total, desc): self.desc = desc
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def update(self, n=1, **kwargs): pass


def _worker_process_stock_tdx(item: Any) -> Optional[dict]:
    """子进程执行单个股票分析"""
    try:
        df = load_daily_data(item.code)
        info = {"code": item.code, "name": item.name, "industry": item.industry}
        res = StockAnalyzer.analyze(df, info)
        return res
    except Exception:
        return None


def run_pipeline(
    limit: Optional[int] = None,
    end_date: Optional[str] = None,
    auto_open: bool = True,
) -> dict:
    """运行完整的指标组合分析流水线"""
    print("🚀 开始新指标组合分析...")
    items = list(iter_stock_items(limit=limit))
    print(f"📋 待分析股票数: {len(items)}")

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

    results = []
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            # 提交任务
            future_to_item = {
                executor.submit(_worker_process_stock_tdx, item): item 
                for item in items
            }
            
            with ProgressBar(len(items), desc="并行分析") as pbar:
                for future in as_completed(future_to_item):
                    res = future.result()
                    if res:
                        results.append(res)
                        pbar.update(1, success=True)
                    else:
                        pbar.update(1, success=False)
    else:
        # 串行执行
        with ProgressBar(len(items), desc="Analyzing") as pbar:
            for item in items:
                try:
                    res = _worker_process_stock_tdx(item)
                    if res:
                        results.append(res)
                    pbar.update(1, success=True)
                except Exception:
                    pbar.update(1, success=False)

    print(f"\n📊 分析完成，命中策略股票数: {len(results)}")

    files: dict = {}
    if results:
        reporter = Reporter(results, end_date)
        csv_path = reporter.save_csv()
        md_path = reporter.save_markdown()
        html_path = reporter.save_html()

        if csv_path:
            files["csv"] = str(csv_path)
            print(f"✅ CSV报告: {csv_path}")
        if md_path:
            files["markdown"] = str(md_path)
            print(f"✅ MD报告:  {md_path}")
        if html_path:
            files["html"] = str(html_path)
            print(f"✅ HTML报告: {html_path}")
            if auto_open:
                print(f"  🌐 自动打开浏览器...")
                url = html_path.as_uri()
                success = webbrowser.open(url)
                if not success and os.name == 'posix':
                    # 尝试 WSL 特有方案
                    try:
                        import subprocess
                        subprocess.run(['wslview', url], check=False, capture_output=True)
                    except:
                        try:
                            import subprocess
                            subprocess.run(['powershell.exe', '-c', f'start "{url}"'], check=False, capture_output=True)
                        except: pass
    else:
        print("⚠️ 未找到符合任何策略的股票")

    return {
        "scanned": len(items),
        "matched": len(results),
        "files": files,
    }
