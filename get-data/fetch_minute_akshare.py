#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取分钟级股票数据 - 使用 AkShare

使用方法：
python fetch_minute_akshare.py --code 600519 --days 5
python fetch_minute_akshare.py --codes 600519,000001,600036 --days 5
python fetch_minute_akshare.py --all --sample 10
"""
from __future__ import annotations
import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import pandas as pd

try:
    import akshare as ak
except ImportError:
    print("请先安装: pip install akshare")
    sys.exit(1)


# 配置
DEFAULT_DAYS = 5
MINUTE_DIR = Path(__file__).resolve().parent / "data" / "minute_akshare"


def get_stock_list() -> List[str]:
    """获取A股股票列表"""
    try:
        stock_list = ak.stock_info_a_code_name()
        codes = stock_list['code'].tolist()
        return [c for c in codes if c.startswith(('0', '3', '6'))]
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return []


def fetch_minute_data(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    获取单只股票的分钟数据
    
    Args:
        code: 股票代码 (如 600519)
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
    
    Returns:
        DataFrame 或 None
    """
    symbol = f"sh{code}" if code.startswith('6') else f"sz{code}"
    
    try:
        # 获取日K数据（AkShare分钟数据有限制）
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        
        if df is None or df.empty:
            return None
        
        # 标准化列名
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '涨跌幅': 'pct_chg',
            '涨跌额': 'change',
            '换手率': 'turnover'
        })
        
        df['date'] = pd.to_datetime(df['date'])
        df['code'] = code
        
        return df
        
    except Exception as e:
        print(f"  ⚠️ {code}: {e}")
        return None


def fetch_realtime_minute(code: str) -> Optional[pd.DataFrame]:
    """
    获取实时分钟数据（当天）
    
    Args:
        code: 股票代码
    
    Returns:
        DataFrame 或 None
    """
    symbol = f"sh{code}" if code.startswith('6') else f"sz{code}"
    
    try:
        # 获取实时分钟数据
        df = ak.stock_zh_a_minute(symbol=symbol)
        
        if df is None or df.empty:
            return None
        
        # 标准化列名
        df = df.rename(columns={
            'day': 'datetime',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        })
        
        df['code'] = code
        
        # 添加日期列
        df['date'] = pd.to_datetime(df['datetime']).dt.date
        
        return df
        
    except Exception as e:
        return None


def merge_minute_data(existing_df: Optional[pd.DataFrame], new_df: pd.DataFrame) -> pd.DataFrame:
    """合并新旧数据"""
    if existing_df is None or existing_df.empty:
        return new_df
    
    # 合并并去重
    combined = pd.concat([existing_df, new_df], ignore_index=True)
    combined = combined.drop_duplicates(subset=['date', 'code'], keep='last')
    combined = combined.sort_values('date')
    combined = combined.reset_index(drop=True)
    
    return combined


def get_realtime_file_path(code: str, data_dir: Path) -> Path:
    """获取实时数据的文件路径"""
    today = datetime.now().strftime('%Y-%m-%d')
    date_dir = data_dir / today
    date_dir.mkdir(parents=True, exist_ok=True)
    return date_dir / f"{code}.csv"


def is_file_valid(file_path: Path, min_rows: int = 100) -> bool:
    """检查文件是否有效（存在且数据足够）"""
    if not file_path.exists():
        return False

    try:
        df = pd.read_csv(file_path)
        return len(df) >= min_rows
    except Exception:
        return False


def save_data(df: pd.DataFrame, code: str, data_dir: Path):
    """保存数据（按日期分类）"""
    data_dir.mkdir(parents=True, exist_ok=True)

    # 按日期分文件夹存储
    if 'datetime' in df.columns and len(df) > 0:
        # 获取数据日期（取最新日期）
        latest_date = pd.to_datetime(df['datetime']).max().strftime('%Y-%m-%d')
        date_dir = data_dir / latest_date
        date_dir.mkdir(parents=True, exist_ok=True)
        file_path = date_dir / f"{code}.csv"
    else:
        file_path = data_dir / f"{code}.csv"

    df.to_csv(file_path, index=False, encoding='utf-8-sig')

    # 返回保存的路径
    return file_path


def main():
    parser = argparse.ArgumentParser(
        description="使用 AkShare 获取股票数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 获取日K数据
  python fetch_minute_akshare.py --code 600519 --days 10
  
  # 获取多只股票
  python fetch_minute_akshare.py --codes 600519,000001 --days 5
  
  # 获取实时分钟数据
  python fetch_minute_akshare.py --code 600519 --realtime
  
  # 获取全市场（采样）
  python fetch_minute_akshare.py --all --sample 20
        """
    )
    
    parser.add_argument("--code", "-c", type=str, help="股票代码")
    parser.add_argument("--codes", type=str, help="逗号分隔的股票代码列表")
    parser.add_argument("--all", action="store_true", help="全市场扫描")
    parser.add_argument("--sample", type=int, help="随机采样数量")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, 
                        help=f"获取天数（默认：{DEFAULT_DAYS}）")
    parser.add_argument("--realtime", action="store_true", 
                        help="获取实时分钟数据")
    parser.add_argument("--start", type=str, help="开始日期 YYYYMMDD")
    parser.add_argument("--end", type=str, help="结束日期 YYYYMMDD")
    
    args = parser.parse_args()
    
    if not args.all and not args.code and not args.codes:
        parser.error("必须指定 --code, --codes 或 --all")
    
    # 计算日期范围
    if args.start and args.end:
        start_date = args.start
        end_date = args.end
    else:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y%m%d')
    
    data_dir = MINUTE_DIR
    
    print("="*60)
    print("AkShare 股票数据获取")
    print("="*60)
    print(f"日期范围: {start_date} ~ {end_date}")
    print(f"数据类型: {'实时分钟' if args.realtime else '日K数据'}")
    print(f"输出目录: {data_dir}")
    print("="*60)
    
    # 确定股票列表
    if args.code:
        codes = [args.code]
    elif args.codes:
        codes = [c.strip() for c in args.codes.split(',')]
    elif args.all:
        print("\n获取股票列表...")
        all_codes = get_stock_list()
        print(f"找到 {len(all_codes)} 只股票")
        
        if args.sample:
            import random
            random.seed(42)
            codes = random.sample(all_codes, min(args.sample, len(all_codes)))
        else:
            codes = all_codes
    
    # 获取数据
    print(f"\n开始获取 {len(codes)} 只股票...")
    success = 0
    fail = 0
    skipped = 0

    for i, code in enumerate(codes):
        if args.realtime:
            # 检查文件是否已存在且有效
            file_path = get_realtime_file_path(code, data_dir)

            if is_file_valid(file_path, min_rows=100):
                print(f"  ⊙ {code}: 跳过（已存在 {len(pd.read_csv(file_path))} 条数据）")
                skipped += 1
                continue

            # 获取实时分钟数据
            df = fetch_realtime_minute(code)
            if df is not None and not df.empty:
                save_data(df, code, data_dir)
                print(f"  ✓ {code}: {len(df)} 条实时数据")
                success += 1
            else:
                fail += 1
        else:
            # 加载现有数据
            existing_file = data_dir / f"{code}.csv"
            existing_df = pd.read_csv(existing_file) if existing_file.exists() else None

            # 获取新数据
            df = fetch_minute_data(code, start_date, end_date)

            if df is not None:
                # 合并
                merged_df = merge_minute_data(existing_df, df)
                save_data(merged_df, code, data_dir)
                print(f"  ✓ {code}: +{len(df)} 条 (总计: {len(merged_df)})")
                success += 1
            else:
                fail += 1

        # 避免请求过快
        if (i + 1) % 10 == 0:
            time.sleep(0.5)

    print(f"\n✓ 完成！成功: {success}, 跳过: {skipped}, 失败: {fail}")
    print(f"数据保存至: {data_dir}")

    # 显示今天已下载的股票数量
    if args.realtime:
        today = datetime.now().strftime('%Y-%m-%d')
        today_dir = data_dir / today
        if today_dir.exists():
            csv_files = list(today_dir.glob('*.csv'))
            print(f"\n今天({today})已下载: {len(csv_files)} 只股票")

    # 显示样本
    if success > 0 and not args.realtime:
        sample_file = data_dir / f"{codes[0]}.csv"
        if sample_file.exists():
            df = pd.read_csv(sample_file)
            print(f"\n【{codes[0]} 样本数据】")
            print(f"  总记录: {len(df)}")
            print(f"  日期范围: {df['date'].min()} ~ {df['date'].max()}")
            print(df.head().to_string())


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
