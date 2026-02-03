# -*- coding: utf-8 -*-
"""
新策略分析主程序
入口脚本
"""
import sys
import os
import argparse
import webbrowser
from pathlib import Path

# Force UTF-8 output for Windows to support emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        # Use 'replace' error handler to avoid UnicodeEncodeError on Windows GBK terminals
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from data_loader import iter_stock_items, load_daily_data
from analyzer import StockAnalyzer
from reporter import Reporter
try:
    from util.progress import ProgressBar
except ImportError:
    # Simple fallback
    class ProgressBar:
        def __init__(self, total, desc): print(desc)
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def update(self, n=1, **kwargs): pass

def main():
    parser = argparse.ArgumentParser(description="运行新策略分析")
    parser.add_argument("--limit", type=int, help="限制分析股票数量(测试用)", default=None)
    parser.add_argument("--end-date", type=str, help="分析截止日期 (YYYY-MM-DD)", default=None)
    args = parser.parse_args()
    
    print("🚀 开始新策略分析...")
    
    # 1. 获取股票列表
    items = list(iter_stock_items(limit=args.limit))
    print(f"📋 待分析股票数: {len(items)}")
    
    results = []
    
    # 2. 遍历分析
    with ProgressBar(len(items), desc="Analyzing") as pbar:
        for item in items:
            try:
                # 加载数据
                df = load_daily_data(item.code)
                
                # 分析
                info = {"code": item.code, "name": item.name, "industry": item.industry}
                res = StockAnalyzer.analyze(df, info)
                
                if res:
                    results.append(res)
                    pbar.update(1, success=True)
                else:
                    pbar.update(1, success=True) # 成功运行但无结果也算成功处理
                    
            except Exception as e:
                # print(f"Error analyzing {item.code}: {e}")
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

        no_browser = os.environ.get("NO_BROWSER", "").lower() in {"1", "true", "yes", "y"}
        if no_browser:
            print("\nNO_BROWSER=1, 跳过自动在浏览器中打开报告。")
        else:
            print(f"\n🌐 正在浏览器中打开报告...")
            webbrowser.open(f"file://{html_path}")
    else:
        print("⚠️ 未找到符合任何策略的股票")

if __name__ == "__main__":
    main()
