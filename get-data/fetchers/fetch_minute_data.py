#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
[L3] fetch_minute_data.py
[ROLE]: 获取 A 股分钟级 (5/15/30/60) K 线数据 (BaoStock)
[INPUT]: BaoStock API
[OUTPUT]: data/minute_{freq}/{code}.csv
[PROTOCOL]: 变更时更新此头部，然后检查 L2/CLAUDE.md

支持频率：
- 5分钟 (frequency='5')
- 15分钟 (frequency='15')  
- 30分钟 (frequency='30')
- 60分钟 (frequency='60')
"""
from __future__ import annotations
import argparse
import importlib
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

# 添加 util 目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
# 兼容在 get-data 下执行的情况
if not (PROJECT_ROOT / "util").exists():
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
util_dir = PROJECT_ROOT / "util"
if str(util_dir) not in sys.path:
    sys.path.append(str(util_dir))

try:
    from progress import ProgressBar
except ImportError:
    class ProgressBar:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def update(self, *args, **kwargs): pass


# 配置
DEFAULT_DAYS = 5  # 获取多少天的数据
DEFAULT_FREQ = '5'  # 默认5分钟频率
BATCH_SIZE = 50  # 批次大小
MINUTE_DIR = Path(__file__).resolve().parent.parent / "data" / "minute_5min"


def get_baostock():
    try:
        return importlib.import_module("baostock")
    except Exception as exc:
        raise RuntimeError("未安装 baostock，请先安装：pip install baostock") from exc


def login_baostock():
    bs = get_baostock()
    lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"BaoStock 登录失败: {lg.error_msg}")


def logout_baostock():
    try:
        bs = get_baostock()
        bs.logout()
    except Exception:
        pass


def fetch_minute_data(bs_code: str, start_date: str, end_date: str, 
                      frequency: str = '5') -> Tuple[pd.DataFrame, Optional[str]]:
    """
    获取分钟级K线数据
    
    Args:
        bs_code: BaoStock格式代码，如 'sh.600519'
        start_date: 开始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD
        frequency: 频率 '5', '15', '30', '60'
    
    Returns:
        (DataFrame, 错误信息)
    """
    bs = get_baostock()
    
    fields = "date,code,open,high,low,close,volume,amount"
    
    rs = bs.query_history_k_data_plus(
        code=bs_code,
        fields=fields,
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,  # 5/15/30/60 分钟
        adjustflag="2",  # 前复权
    )
    
    if rs.error_code != "0":
        return pd.DataFrame(), rs.error_msg
    
    rows = []
    while rs.next():
        rows.append(rs.get_row_data())
    
    if not rows:
        return pd.DataFrame(), None
    
    df = pd.DataFrame(rows, columns=rs.fields)
    
    # 数据类型转换
    df["date"] = pd.to_datetime(df["date"])
    for col in ["open", "high", "low", "close", "volume", "amount", "pctChg"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # 提取股票代码
    df["code"] = df["code"].str.split(".").str[1]
    
    # 提取时间（去掉日期部分，只保留 HH:MM:SS）
    df["time"] = df["date"].dt.strftime("%H:%M:%S")
    df["datetime"] = df["date"]
    
    return df, None


def get_stock_list() -> List[str]:
    """获取股票列表"""
    bs = get_baostock()
    rs = bs.query_stock_basic()
    
    if rs.error_code != "0":
        raise RuntimeError(f"获取股票列表失败: {rs.error_msg}")
    
    stocks = []
    while rs.next():
        row = rs.get_row_data()
        code = row[1]  # code 字段
        if code and code.startswith(("sh.", "sz.")):
            stocks.append(code)
    
    return stocks


def load_existing_minute_data(code: str, minute_dir: Path) -> Optional[pd.DataFrame]:
    """加载已有的分钟数据"""
    file_path = minute_dir / f"{code}.csv"
    if not file_path.exists():
        return None
    
    try:
        df = pd.read_csv(file_path)
        df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception:
        return None


def save_minute_data(df: pd.DataFrame, code: str, minute_dir: Path):
    """保存分钟数据"""
    minute_dir.mkdir(parents=True, exist_ok=True)
    file_path = minute_dir / f"{code}.csv"
    df.to_csv(file_path, index=False, encoding='utf-8-sig')


def merge_minute_data(existing_df: Optional[pd.DataFrame], new_df: pd.DataFrame) -> pd.DataFrame:
    """合并新旧分钟数据"""
    if existing_df is None or existing_df.empty:
        return new_df
    
    # 合并并去重
    combined = pd.concat([existing_df, new_df], ignore_index=True)
    combined = combined.drop_duplicates(subset=['date', 'code'], keep='last')
    combined = combined.sort_values('date')
    combined = combined.reset_index(drop=True)
    
    return combined


def compute_date_range(days: int) -> Tuple[str, str]:
    """计算日期范围"""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return start_date, end_date


def fetch_single_stock(code: str, start_date: str, end_date: str, 
                       frequency: str, minute_dir: Path) -> bool:
    """获取单只股票的分钟数据"""
    # 转换代码格式
    bs_code = f"sh.{code}" if code.startswith('6') else f"sz.{code}"
    
    # 加载现有数据
    existing_df = load_existing_minute_data(code, minute_dir)
    
    # 计算需要获取的日期范围
    if existing_df is not None and not existing_df.empty:
        last_date = existing_df["date"].max()
        if pd.notna(last_date):
            start_date = (pd.Timestamp(last_date) + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 获取新数据
    new_df, error_msg = fetch_minute_data(bs_code, start_date, end_date, frequency)
    
    if error_msg:
        print(f"  ⚠️ {code}: {error_msg}")
        return False
    
    if new_df.empty:
        return False
    
    # 合并数据
    merged_df = merge_minute_data(existing_df, new_df)
    
    # 保存
    save_minute_data(merged_df, code, minute_dir)
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="获取分钟级股票数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 获取单只股票（最近5天，5分钟频率）
  python fetch_minute_data.py --code 600519
  
  # 获取多只股票
  python fetch_minute_data.py --codes 600519,000001,600036
  
  # 全市场获取（最近5天，5分钟频率）
  python fetch_minute_data.py --all --days 5
  
  # 15分钟频率
  python fetch_minute_data.py --code 600519 --freq 15
  
  # 查看帮助
  python fetch_minute_data.py --help
        """
    )
    
    parser.add_argument("--code", "-c", type=str, help="股票代码（如：600519）")
    parser.add_argument("--codes", type=str, help="逗号分隔的股票代码列表")
    parser.add_argument("--all", action="store_true", help="全市场扫描")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, 
                        help=f"获取天数（默认：{DEFAULT_DAYS}）")
    parser.add_argument("--freq", type=str, default=DEFAULT_FREQ,
                        choices=['5', '15', '30', '60'],
                        help=f"分钟频率（默认：{DEFAULT_FREQ}）")
    parser.add_argument("--sample", type=int, help="随机采样数量（仅--all时生效）")
    parser.add_argument("--start", type=str, help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="结束日期 YYYY-MM-DD")
    
    args = parser.parse_args()
    
    # 验证参数
    if not args.all and not args.code and not args.codes:
        parser.error("必须指定 --code, --codes 或 --all")
    
    # 设置日期范围
    if args.start and args.end:
        start_date = args.start
        end_date = args.end
    else:
        start_date, end_date = compute_date_range(args.days)
    
    # 设置输出目录
    freq_dir = {'5': 'minute_5min', '15': 'minute_15min', '30': 'minute_30min', '60': 'minute_60min'}
    minute_dir = Path(__file__).resolve().parent.parent / "data" / freq_dir[args.freq]
    
    print("="*60)
    print("分钟级股票数据获取")
    print("="*60)
    print(f"频率: {args.freq}分钟")
    print(f"日期范围: {start_date} ~ {end_date}")
    print(f"输出目录: {minute_dir}")
    print("="*60)
    
    # 登录
    login_baostock()
    print("✓ BaoStock 登录成功")
    
    try:
        # 确定股票列表
        if args.code:
            codes = [args.code]
        elif args.codes:
            codes = [c.strip() for c in args.codes.split(',')]
        elif args.all:
            print("\n获取股票列表...")
            stocks = get_stock_list()
            print(f"找到 {len(stocks)} 只股票")
            
            if args.sample:
                import random
                random.seed(42)
                codes = random.sample(stocks, min(args.sample, len(stocks)))
            else:
                codes = stocks
        
        # 获取数据
        print(f"\n开始获取 {len(codes)} 只股票的数据...")
        success = 0
        fail = 0
        
        with ProgressBar(len(codes), desc="获取进度") as pbar:
            for i, bs_code in enumerate(codes):
                # 提取纯代码
                code = bs_code.split('.')[-1] if '.' in bs_code else bs_code
                
                if fetch_single_stock(code, start_date, end_date, args.freq, minute_dir):
                    success += 1
                else:
                    fail += 1
                
                pbar.update(1, success=success)
                
                # 避免请求过快
                if (i + 1) % 10 == 0:
                    time.sleep(0.5)
        
        print(f"\n✓ 完成！成功: {success}, 失败: {fail}")
        print(f"数据保存至: {minute_dir}")
        
        # 显示样本数据
        if success > 0:
            sample_file = minute_dir / f"{codes[0]}.csv"
            if sample_file.exists():
                df = pd.read_csv(sample_file)
                print(f"\n【样本数据】{codes[0]}")
                print(f"  总记录数: {len(df)}")
                print(f"  日期范围: {df['date'].min()} ~ {df['date'].max()}")
                print(f"  数据字段: {list(df.columns)}")
                print(f"\n前5条:")
                print(df.head().to_string(index=False))
    
    finally:
        logout_baostock()
        print("\n✓ BaoStock 已退出")


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
