# -*- coding: utf-8 -*-
"""
TD九底分析系统 - 主入口

使用方法:
    无参数            全量扫描
    --test            测试模式（10只股票）
    --random-test     随机测试（50只股票）
    python main.py --days 180         # 分析最近180天
    python main.py --no-html          # 不生成HTML
    python main.py --no-open          # 不自动打开浏览器
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Force UTF-8 output for Windows to support emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        # Use 'replace' error handler to avoid UnicodeEncodeError on Windows GBK terminals
        # This will print '?' instead of crashing for unsupported emojis
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass

# 确保模块路径正确
sys.path.insert(0, str(Path(__file__).parent))

from pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="TD九底分析系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
运行模式（默认全量）:
    无参数           全量扫描
    --test           测试 10 只
    --random-test    随机测试 50 只
示例:
    python main.py --days 180         # 分析最近180天
    python main.py --level 三周期九底  # 只筛选三周期九底
        """
    )
    
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="测试模式，10 只股票"
    )
    
    parser.add_argument(
        "--random-test",
        action="store_true",
        help="随机测试，50 只股票"
    )
    
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="[高级] 限制分析的股票数量（未传 --test/--random-test 时生效）"
    )
    
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=365,
        help="分析最近多少天的数据 (默认: 365)"
    )
    
    parser.add_argument(
        "--level",
        type=str,
        nargs="+",
        default=None,
        help="筛选的共振级别，如: 三周期九底 双周期九底"
    )
    
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="不生成HTML报告"
    )
    
    parser.add_argument(
        "--no-markdown",
        action="store_true",
        help="不生成Markdown报告"
    )
    
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="不自动打开浏览器"
    )
    
    parser.add_argument(
        "--skip-fetch", "-sf", "--all", "-all",
        action="store_true",
        help="跳过网络获取，直接读取raw目录里的所有股票"
    )
    
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="分析截止日期 (YYYY-MM-DD)"
    )
    
    args = parser.parse_args()
    
    # 运行模式：--random-test 优先于 --test，否则用 --limit（None=全量）
    if args.random_test:
        limit = 50
    elif args.test:
        limit = 10
    else:
        limit = args.limit
    
    filter_levels = args.level
    if filter_levels is None:
        filter_levels = ["三周期9底", "双周期9底", "单周期9底"]
    
    # 运行分析
    try:
        result = run_pipeline(
            days=args.days,
            limit=limit,
            generate_html=not args.no_html,
            generate_markdown=not args.no_markdown,
            auto_open=not args.no_open,
            filter_levels=filter_levels,
            skip_fetch=args.skip_fetch,
            end_date=args.end_date,
        )
        
        # 输出摘要
        print(f"\n📊 分析摘要:")
        print(f"   总股票数: {result.get('total', 0)}")
        print(f"   筛选后: {result.get('filtered', 0)}")
        
        if result.get("files"):
            print(f"\n📁 生成文件:")
            for ftype, fpath in result["files"].items():
                print(f"   {ftype}: {fpath}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
