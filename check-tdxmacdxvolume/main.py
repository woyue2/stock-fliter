# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  --limit int, --end-date str（CLI 参数）
# OUTPUT: None（生成 CSV/MD/HTML 报告，自动打开浏览器）
# POS:    check-tdxmacdxvolume/main.py（Phase 3 对齐架构）
# -*- coding: utf-8 -*-
"""
新策略分析主程序
入口脚本
"""
import sys
import argparse
import webbrowser
from pathlib import Path

# Force UTF-8 output for Windows to support emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass

# 确保模块根目录和项目根在 sys.path
_MOD = Path(__file__).resolve().parent
_ROOT = _MOD.parent
for _p in [str(_MOD), str(_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from data_loader import iter_stock_items, load_daily_data
from analyzers import StockAnalyzer          # ← Phase 3: 从 analyzers/ 包导入
from reporter import Reporter

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


def main():
    parser = argparse.ArgumentParser(description="运行 TDxMACDxVolume 分析")
    parser.add_argument("--limit", type=int, help="限制分析股票数量(测试用)", default=None)
    parser.add_argument("--end-date", type=str, help="分析截止日期 (YYYY-MM-DD)", default=None)
    args = parser.parse_args()

    print("🚀 开始 TDxMACDxVolume 分析...")

    # 1. 获取股票列表
    items = list(iter_stock_items(limit=args.limit))
    print(f"📋 待分析股票数: {len(items)}")

    results = []

    # 2. 遍历分析
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

    # 3. 生成报告
    print(f"\n📊 分析完成，命中策略股票数: {len(results)}")
    if results:
        reporter = Reporter(results, args.end_date)
        csv_path = reporter.save_csv()
        md_path = reporter.save_markdown()
        html_path = reporter.save_html()

        print(f"✅ CSV报告: {csv_path}")
        print(f"✅ MD报告:  {md_path}")
        print(f"✅ HTML报告: {html_path}")

        print(f"\n🌐 正在浏览器中打开报告...")
        webbrowser.open(f"file://{html_path}")
    else:
        print("⚠️ 未找到符合任何策略的股票")


if __name__ == "__main__":
    main()
