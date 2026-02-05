#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
真实股票数据分钟级分析

使用新方法分析你的真实股票数据：
- 从日K数据估算分钟级走势
- 生成240维向量
- 识别形态并与典型模式对比
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from minute_pattern_analyzer import MinutePatternAnalyzer, MinuteDataLoader


def load_minute_data(code: str, data_dir: Path) -> pd.DataFrame:
    """加载真实分钟级数据（支持日期文件夹结构）"""
    akshare_dir = data_dir / "minute_akshare"
    
    if akshare_dir.exists():
        # 查找最新的日期文件夹
        date_dirs = sorted([d for d in akshare_dir.iterdir() if d.is_dir()], reverse=True)
        
        for date_dir in date_dirs:
            file_path = date_dir / f"{code}.csv"
            if file_path.exists():
                df = pd.read_csv(file_path)
                if 'datetime' in df.columns:
                    df['datetime'] = pd.to_datetime(df['datetime'])
                return df
    
    # 兼容旧结构（根目录下的CSV）
    file_path = akshare_dir / f"{code}.csv"
    if file_path.exists():
        df = pd.read_csv(file_path)
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        return df
    
    return pd.DataFrame()


def load_daily_data(code: str, data_dir: Path) -> pd.DataFrame:
    """加载单只股票的日K数据"""
    file_path = data_dir / f"{code}.csv"
    if not file_path.exists():
        return pd.DataFrame()
    
    df = pd.read_csv(file_path, encoding='utf-8-sig')
    
    # 标准化列名
    if '日期' in df.columns:
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        })
    
    # 转换日期
    df['date'] = pd.to_datetime(df['date'])
    
    # 确保数值列
    for col in ['open', 'close', 'high', 'low']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df.sort_values('date').reset_index(drop=True)


def analyze_stock(code: str, data_dir: Path, date: str = None, use_real_minute: bool = True):
    """分析单只股票"""
    print(f"\n{'='*60}")
    print(f"股票代码: {code}")
    print(f"{'='*60}")
    
    loader = MinuteDataLoader(str(data_dir))
    analyzer = MinutePatternAnalyzer(normalize=True)
    
    # 尝试真实分钟数据（优先 AkShare）
    real_minute_df = None
    
    if use_real_minute:
        # 检查 AkShare 数据目录
        akshare_dir = data_dir.parent / "minute_akshare"
        if akshare_dir.exists():
            real_minute_df = load_minute_data(code, data_dir)
            if not real_minute_df.empty:
                print(f"✓ 使用 AkShare 真实分钟级数据")
    
    # 使用真实分钟数据或回退到日K估算
    if real_minute_df is not None and not real_minute_df.empty:
        # 确定日期列名
        date_col = 'datetime' if 'datetime' in real_minute_df.columns else 'date'
        
        # 筛选日期
        if date:
            target_dt = pd.to_datetime(date)
            minute_df = real_minute_df[real_minute_df[date_col].dt.date == target_dt.date()]
        else:
            # 取最后一天（按日期部分过滤）
            last_date = real_minute_df[date_col].max()
            last_date_date = last_date.date()
            minute_df = real_minute_df[real_minute_df[date_col].dt.date == last_date_date]
        
        if minute_df.empty:
            print(f"⚠️ 指定日期无数据，回退到日K估算")
        elif len(minute_df) < 48:
            print(f"⚠️ 分钟数据仅{len(minute_df)}条，不足48条")
        else:
            # 使用真实分钟数据
            print(f"分析日期: {minute_df[date_col].max().strftime('%Y-%m-%d %H:%M')}")
            print(f"开盘价: {minute_df.iloc[0]['open']:.2f}")
            print(f"收盘价: {minute_df.iloc[-1]['close']:.2f}")
            print(f"最高价: {minute_df['high'].max():.2f}")
            print(f"最低价: {minute_df['low'].min():.2f}")
            print(f"分钟数据条数: {len(minute_df)}")
            
            vector = minute_df['close'].values
            base_price = vector[0]
            vector_normalized = (vector - base_price) / base_price * 100
            
            print(f"\n【真实分钟走势】")
            print(f"  向量维度: {len(vector_normalized)}")
            print(f"  开盘→收盘变化: {vector_normalized[0]:.2f}% → {vector_normalized[-1]:.2f}%")
            print(f"  最高点: {np.max(vector_normalized):.2f}%")
            print(f"  最低点: {np.min(vector_normalized):.2f}%")
            
            # 创建DataFrame用于分析
            minute_for_analysis = pd.DataFrame({'close': minute_df['close'].values})
            result = analyzer.analyze_single_stock(minute_for_analysis)
            
            _print_analysis_result(result, code)
            return result
    
    # 回退到日K估算
    print(f"⚠️ 无真实分钟数据，使用日K估算")
    
    df = load_daily_data(code, data_dir)
    if df.empty:
        print(f"❌ 未找到股票 {code} 的数据")
        return None
    
    # 选择日期
    if date:
        target_date = pd.to_datetime(date)
        df_target = df[df['date'] == target_date]
        if df_target.empty:
            df_target = df.tail(2)
    else:
        df_target = df.tail(2)
    
    if df_target.empty:
        print(f"❌ 数据不足")
        return None
    
    latest = df_target.iloc[-1]
    print(f"分析日期: {latest['date'].strftime('%Y-%m-%d')}")
    print(f"开盘价: {latest['open']:.2f}")
    print(f"收盘价: {latest['close']:.2f}")
    print(f"最高价: {latest['high']:.2f}")
    print(f"最低价: {latest['low']:.2f}")
    
    # 估算分钟级走势
    vector = loader.estimate_minute_from_daily(df_target)
    
    print(f"\n【估算的分钟级走势】")
    print(f"  向量维度: {len(vector)}")
    print(f"  开盘→收盘变化: {vector[0]:.2f}% → {vector[-1]:.2f}%")
    print(f"  最高点: {np.max(vector):.2f}%")
    print(f"  最低点: {np.min(vector):.2f}%")
    print(f"  波动范围: {np.max(vector) - np.min(vector):.2f}%")
    
    # 分析
    minute_df = pd.DataFrame({'close': vector + latest['open']})
    result = analyzer.analyze_single_stock(minute_df)
    
    _print_analysis_result(result, code, analyzer)
    return result


def _print_analysis_result(result, code, analyzer=None):
    """打印分析结果"""
    print(f"\n【形态分析结果】")
    print(f"  形态类型: {result['pattern_name']}")
    print(f"  形态代码: {result['pattern_code']}")
    
    f = result['features']
    print(f"\n【详细指标】")
    print(f"  日内收益: {f['intraday_return']:.2f}%")
    print(f"  趋势斜率: {f['trend_slope']:.4f} ({f['trend_direction']})")
    print(f"  波动率: {f['volatility']:.2f}")
    print(f"  最大涨幅: {f['max_gain']:.2f}%")
    print(f"  最大回撤: {f['max_drawdown']:.2f}%")
    
    print(f"\n【早盘 vs 午盘】")
    print(f"  早盘平均: {f['morning_mean']:.2f}%")
    print(f"  午盘平均: {f['afternoon_mean']:.2f}%")
    print(f"  差异: {f['morning_afternoon_diff']:+.2f}%")
    
    if f['v_shape']:
        print(f"\n【V型特征】")
        print(f"  检测到V型形态")
        print(f"  最低点位置: {f['v_position']:.0%} (0=开盘, 1=收盘)")
    
    if f['inverted_v_shape']:
        print(f"\n【倒V型特征】")
        print(f"  检测到倒V型形态")
        print(f"  最高点位置: {f['inverted_v_position']:.0%}")
    
    print(f"\n【与典型形态相似度】")
    for pattern_type, similarity in result['similarities'].items():
        if analyzer:
            name = analyzer.PATTERN_NAMES.get(pattern_type, pattern_type)
        else:
            name = pattern_type
        bar = "█" * int(similarity * 20)
        print(f"  {name:<10}: {similarity:.3f} {bar}")
    
    return result


def compare_stocks(codes: list, data_dir: Path, date: str = None):
    """比较多只股票的走势"""
    print(f"\n{'='*60}")
    print(f"多股票走势对比分析")
    print(f"{'='*60}")
    
    analyzer = MinutePatternAnalyzer(normalize=True)
    loader = MinuteDataLoader(str(data_dir))
    
    vectors = {}
    results = {}
    
    for code in codes:
        df = load_daily_data(code, data_dir)
        if df.empty:
            continue
        
        if date:
            target_date = pd.to_datetime(date)
            df = df[df['date'] <= target_date].tail(2)
        else:
            df = df.tail(2)
        
        if df.empty:
            continue
        
        vector = loader.estimate_minute_from_daily(df)
        vectors[code] = vector
        
        minute_df = pd.DataFrame({'close': vector + df.iloc[-1]['open']})
        results[code] = analyzer.analyze_single_stock(minute_df)
    
    if len(vectors) < 2:
        print("⚠️ 需要至少2只股票进行对比")
        return
    
    print(f"\n【形态分布】")
    pattern_counts = {}
    for code, result in results.items():
        pattern = result['pattern_name']
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        print(f"  {code}: {pattern}")
    
    print(f"\n【相似度矩阵】")
    print(f"{'代码':<8}", end="")
    for code in vectors.keys():
        print(f"{code:<8}", end="")
    print()
    print("-" * 8 * (len(vectors) + 1))
    
    codes_list = list(vectors.keys())
    for i, code1 in enumerate(codes_list):
        print(f"{code1:<8}", end="")
        for j, code2 in enumerate(codes_list):
            if i == j:
                print(f"  1.000  ", end="")
            else:
                sim = analyzer.compare_stocks(vectors[code1], vectors[code2])
                print(f" {sim['cosine_similarity']:>6.3f}  ", end="")
        print()
    
    print(f"\n【解读】")
    print("  - 相似度 > 0.9: 走势高度相似，可能存在联动")
    print("  - 相似度 0.7-0.9: 走势较为相似")
    print("  - 相似度 < 0.5: 走势差异明显")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="真实股票分钟级走势分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 分析单只股票
  python analyze_real_stocks.py --code 600519
  
  # 分析指定日期
  python analyze_real_stocks.py --code 600519 --date 2026-01-30
  
  # 对比多只股票
  python analyze_real_stocks.py --codes 600519,000001,600036
  
  # 分析目录下所有股票
  python analyze_real_stocks.py --all
        """
    )
    
    parser.add_argument("--code", "-c", type=str, help="股票代码")
    parser.add_argument("--codes", type=str, help="逗号分隔的股票代码列表")
    parser.add_argument("--date", "-d", type=str, help="分析日期 (YYYY-MM-DD)")
    parser.add_argument("--all", action="store_true", help="分析目录下所有股票")
    
    args = parser.parse_args()
    
    # 设置路径
    base_dir = Path(__file__).resolve().parent
    raw_dir = base_dir.parent / "get-data" / "data" / "raw"
    
    print("="*60)
    print("真实股票分钟级走势分析")
    print("方法：日K数据 → 估算分钟级走势 → 240维向量分析")
    print("="*60)
    
    if args.all:
        # 分析所有股票
        print(f"\n扫描目录: {raw_dir}")
        stock_files = list(raw_dir.glob("*.csv"))[:20]  # 限制前20只
        print(f"找到 {len(list(raw_dir.glob('*.csv')))} 只股票，分析前20只...\n")
        
        codes = [f.stem for f in stock_files]
        compare_stocks(codes, raw_dir, args.date)
        
    elif args.codes:
        # 多股票对比
        codes = [c.strip() for c in args.codes.split(',')]
        compare_stocks(codes, raw_dir, args.date)
        
    elif args.code:
        # 单股票分析
        result = analyze_stock(args.code, raw_dir, args.date)
        if result:
            print(f"\n【下一步】")
            print(f"  1. 可结合多日数据分析趋势变化")
            print(f"  2. 可与同行业股票对比走势相似度")
            print(f"  3. 可积累历史形态数据训练模型")
    else:
        # 默认演示
        print("\n📌 使用示例:")
        print("  python analyze_real_stocks.py --code 600519")
        print("  python analyze_real_stocks.py --codes 600519,000001")
        print("  python analyze_real_stocks.py --all")
        
        print("\n" + "="*60)
        print("演示：分析贵州茅台(600519)")
        print("="*60)
        result = analyze_stock("600519", raw_dir, None)


if __name__ == "__main__":
    main()
