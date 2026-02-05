#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量形态分析 - 快速了解市场整体情况

使用方法：
python batch_analyze.py                    # 分析所有有数据的股票
python batch_analyze.py --sample 100      # 随机采样100只
python batch_analyze.py --top 20          # 显示TOP20强势/弱势股
python batch_analyze.py --save            # 保存详细结果
"""
from __future__ import annotations
import argparse
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

from minute_pattern_analyzer import MinutePatternAnalyzer, MinuteDataLoader


def load_minute_data(code: str, data_dir: Path) -> pd.DataFrame:
    """加载分钟数据"""
    akshare_dir = data_dir / "minute_akshare"
    file_path = akshare_dir / f"{code}.csv"
    
    if file_path.exists():
        df = pd.read_csv(file_path)
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        return df
    return pd.DataFrame()


def load_daily_data(code: str, data_dir: Path) -> pd.DataFrame:
    """加载日K数据"""
    file_path = data_dir / f"{code}.csv"
    if not file_path.exists():
        return pd.DataFrame()
    
    df = pd.read_csv(file_path, encoding='utf-8-sig')
    
    if '日期' in df.columns:
        df = df.rename(columns={'日期': 'date', '开盘': 'open', '收盘': 'close', 
                               '最高': 'high', '最低': 'low'})
    
    for col in ['open', 'close', 'high', 'low']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    return df.sort_values('date').reset_index(drop=True)


def analyze_stock(code: str, raw_dir: Path, minute_dir: Path) -> dict:
    """分析单只股票"""
    analyzer = MinutePatternAnalyzer(normalize=True)
    loader = MinuteDataLoader(str(raw_dir))
    
    # 优先使用真实分钟数据
    minute_df = load_minute_data(code, minute_dir)
    use_minute = False
    
    if not minute_df.empty:
        # 取最后一天
        if 'datetime' in minute_df.columns:
            last_date = minute_df['datetime'].max()
            last_date_date = last_date.date()
            minute_df = minute_df[minute_df['datetime'].dt.date == last_date_date]
        
        if len(minute_df) >= 10:
            use_minute = True
    
    if use_minute:
        # 使用真实分钟数据
        vector = minute_df['close'].values
        base_price = vector[0]
        vector_norm = (vector - base_price) / base_price * 100
        
        minute_for_analysis = pd.DataFrame({'close': minute_df['close'].values})
        result = analyzer.analyze_single_stock(minute_for_analysis)
        
        return {
            'code': code,
            'pattern': result['pattern_name'],
            'return': result['features']['intraday_return'],
            'volatility': result['features']['volatility'],
            'data_source': 'minute',
            'data_points': len(minute_df)
        }
    else:
        # 使用日K估算
        df = load_daily_data(code, raw_dir)
        if df.empty:
            return None
        
        latest = df.tail(1).iloc[0]
        vector = loader.estimate_minute_from_daily(df.tail(2))
        
        minute_df = pd.DataFrame({'close': vector + latest['open']})
        result = analyzer.analyze_single_stock(minute_df)
        
        return {
            'code': code,
            'pattern': result['pattern_name'],
            'return': result['features']['intraday_return'],
            'volatility': result['features']['volatility'],
            'data_source': 'daily_estimate',
            'data_points': 240
        }


def main():
    parser = argparse.ArgumentParser(
        description="批量形态分析 - 快速了解市场整体情况",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python batch_analyze.py              # 分析全部
  python batch_analyze.py --sample 100 # 采样100只
  python batch_analyze.py --top 20     # TOP20排名
  python batch_analyze.py --save       # 保存详细结果
        """
    )
    
    parser.add_argument("--sample", type=int, help="随机采样数量")
    parser.add_argument("--top", type=int, default=10, help="TOP排名数量")
    parser.add_argument("--save", action="store_true", help="保存详细结果")
    parser.add_argument("--dir", type=str, default="../get-data/data/raw", help="数据目录")
    
    args = parser.parse_args()
    
    raw_dir = Path(__file__).resolve().parent / args.dir
    minute_dir = raw_dir.parent / "minute_akshare"
    
    print("="*70)
    print("批量形态分析 - 市场整体情况概览")
    print("="*70)
    
    # 获取股票列表
    stock_files = list(raw_dir.glob("*.csv"))
    
    if args.sample:
        import random
        random.seed(42)
        stock_files = random.sample(stock_files, min(args.sample, len(stock_files)))
    
    print(f"\n分析股票数: {len(stock_files)} 只")
    print(f"数据目录: {raw_dir}")
    print()
    
    # 批量分析
    results = []
    for i, f in enumerate(stock_files):
        code = f.stem
        result = analyze_stock(code, raw_dir, minute_dir)
        if result:
            results.append(result)
        
        if (i + 1) % 500 == 0:
            print(f"  进度: {i+1}/{len(stock_files)}")
    
    if not results:
        print("❌ 未找到有效数据")
        return
    
    df = pd.DataFrame(results)
    
    # 统计形态分布
    print("="*70)
    print("【形态分布统计】")
    print("="*70)
    
    pattern_counts = df['pattern'].value_counts()
    total = len(df)
    
    print(f"\n{'形态类型':<15} {'数量':>8} {'占比':>8}")
    print("-" * 35)
    
    for pattern, count in pattern_counts.items():
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"{pattern:<15} {count:>8} {pct:>7.1f}% {bar}")
    
    print("-" * 35)
    print(f"{'总计':<15} {total:>8}")
    
    # 整体统计
    print("\n" + "="*70)
    print("【整体市场指标】")
    print("="*70)
    
    avg_return = df['return'].mean()
    std_return = df['return'].std()
    up_count = len(df[df['return'] > 0])
    down_count = len(df[df['return'] < 0])
    
    print(f"\n平均日内收益: {avg_return:+.2f}%")
    print(f"收益标准差: {std_return:.2f}%")
    print(f"上涨/下跌: {up_count}/{down_count} ({up_count/total*100:.1f}%/{down_count/total*100:.1f}%)")
    
    # 数据来源
    minute_count = len(df[df['data_source'] == 'minute'])
    print(f"\n数据来源: 真实分钟 {minute_count} 只, 日K估算 {total - minute_count} 只")
    
    # TOP排名
    print("\n" + "="*70)
    print(f"【TOP {args.top} 强势股】")
    print("="*70)
    
    top_up = df.nlargest(args.top, 'return')
    for i, row in top_up.iterrows():
        marker = "✓" if row['data_source'] == 'minute' else "~"
        print(f"  {marker} {row['code']:<10} {row['return']:>+6.2f}%  ({row['pattern']})")
    
    print(f"\n【TOP {args.top} 弱势股】")
    print("-"*50)
    
    top_down = df.nsmallest(args.top, 'return')
    for i, row in top_down.iterrows():
        marker = "✓" if row['data_source'] == 'minute' else "~"
        print(f"  {marker} {row['code']:<10} {row['return']:>+6.2f}%  ({row['pattern']})")
    
    # 市场情绪判断
    print("\n" + "="*70)
    print("【市场情绪判断】")
    print("="*70)
    
    if avg_return > 1:
        sentiment = "🔥 偏热 - 整体上涨"
    elif avg_return > 0.3:
        sentiment = "📈 偏强 - 小幅上涨"
    elif avg_return > -0.3:
        sentiment = "➡️ 震荡 - 方向不明"
    elif avg_return > -1:
        sentiment = "📉 偏弱 - 小幅下跌"
    else:
        sentiment = "❄️ 偏冷 - 整体下跌"
    
    print(f"\n  {sentiment}")
    print(f"  上涨家数占比: {up_count/total*100:.1f}%")
    print(f"  平均波动率: {df['volatility'].mean():.2f}")
    
    # 保存结果
    if args.save:
        output_dir = Path(__file__).resolve().parent / "output"
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = output_dir / f"batch_analysis_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"\n✓ 详细结果已保存: {csv_file}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
