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
from __future__ import annotations

import sys
import webbrowser
from pathlib import Path
from typing import Optional

# 确保项目根在 sys.path（供 util 导入）
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# 本模块根目录也要在 path（供同级 import）
_MOD = Path(__file__).resolve().parent
if str(_MOD) not in sys.path:
    sys.path.insert(0, str(_MOD))

from data_loader import iter_stock_items, load_daily_data  # noqa: E402
from analyzers import StockAnalyzer  # noqa: E402
from reporter import Reporter  # noqa: E402

try:
    from util.progress import ProgressBar
except ImportError:
    try:
        from tqdm import tqdm
        class ProgressBar:
            def __init__(self, total, desc):
                self.pbar = tqdm(total=total, desc=desc)
            def __enter__(self): return self
            def __exit__(self, *args): self.pbar.close()
            def update(self, n=1, **kwargs): self.pbar.update(n)
    except ImportError:
        class ProgressBar:  # type: ignore
            def __init__(self, total, desc): print(f"开始: {desc}")
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def update(self, n=1, **kwargs): pass


def run_pipeline(
    limit: Optional[int] = None,
    end_date: Optional[str] = None,
    auto_open: bool = True,
) -> dict:
    """
    运行完整的指标组合分析流水线

    Args:
        limit:     限制分析股票数量（None=全量）
        end_date:  分析截止日期，YYYY-MM-DD 格式
        auto_open: 是否自动在浏览器打开报告

    Returns:
        包含 scanned/matched/files 的摘要字典
    """
    print("🚀 开始新指标组合分析...")
    items = list(iter_stock_items(limit=limit))
    print(f"📋 待分析股票数: {len(items)}")

    results = []
    with ProgressBar(len(items), desc="Analyzing") as pbar:
        for item in items:
            try:
                df = load_daily_data(item.code)
                info = {"code": item.code, "name": item.name, "industry": item.industry}
                res = StockAnalyzer.analyze(df, info)
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
                webbrowser.open(f"file://{html_path}")
    else:
        print("⚠️ 未找到符合任何策略的股票")

    return {
        "scanned": len(items),
        "matched": len(results),
        "files": files,
    }
