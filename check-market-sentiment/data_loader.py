# -*- coding: utf-8 -*-
"""
数据加载器 - 从 stocks_index 目录加载多天的股票数据
"""
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional, List, Dict
import sys
import pandas as pd

# 添加 util 目录到路径
parent_dir = Path(__file__).resolve().parent.parent
util_dir = parent_dir / "util"
if str(util_dir) not in sys.path:
    sys.path.insert(0, str(util_dir))

try:
    from progress import ProgressBar
except ImportError:
    # 兼容性回退
    class ProgressBar:
        def __init__(self, *args, **kwargs): 
            self.total = args[0] if args else 0
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def update(self, *args, **kwargs): pass


class MarketDataLoader:
    """市场数据加载器 - 从 stocks_index 目录加载"""
    
    def __init__(self, stocks_index_dir: Path):
        """
        初始化数据加载器
        
        Args:
            stocks_index_dir: stocks_index 目录路径 (get-data/data/stocks_index)
        """
        self.stocks_index_dir = Path(stocks_index_dir)
        
        if not self.stocks_index_dir.exists():
            raise FileNotFoundError(f"stocks_index 目录不存在: {self.stocks_index_dir}")
    
    def get_available_dates(self) -> List[str]:
        """
        获取所有可用的日期
        
        Returns:
            日期列表，格式: ['2026-01-28', '2026-01-29', '2026-01-30']
        """
        dates = []
        for date_dir in self.stocks_index_dir.iterdir():
            if date_dir.is_dir() and date_dir.name.count('-') == 2:
                # 验证是否是有效的日期格式
                try:
                    datetime.strptime(date_dir.name, '%Y-%m-%d')
                    dates.append(date_dir.name)
                except ValueError:
                    continue
        
        return sorted(dates)
    
    def load_single_date(self, target_date: str, show_progress: bool = False) -> pd.DataFrame:
        """
        加载指定日期的数据（从 stocks_index 获取股票列表，从 raw 目录获取价格数据）
        
        Args:
            target_date: 目标日期，格式: '2026-01-30'
            show_progress: 是否显示进度条
        
        Returns:
            股票数据 DataFrame
        """
        date_dir = self.stocks_index_dir / target_date
        csv_file = date_dir / "stocks_index.csv"
        
        if not csv_file.exists():
            print(f"警告: {target_date} 的数据文件不存在: {csv_file}")
            return pd.DataFrame()
        
        try:
            # 1. 读取 stocks_index.csv 获取股票列表
            index_df = pd.read_csv(csv_file, encoding='utf-8-sig')
            
            # 标准化列名
            if '代码' in index_df.columns:
                column_mapping = {
                    '代码': 'code',
                    '名称': 'name',
                    '行业': 'industry',
                }
                index_df = index_df.rename(columns=column_mapping)
            
            # 确保 code 是字符串并补齐6位
            if 'code' not in index_df.columns:
                print(f"错误: {target_date} 的索引文件缺少 'code' 列")
                return pd.DataFrame()
            
            index_df['code'] = index_df['code'].astype(str).str.zfill(6)
            
            # 2. 从 raw 目录加载价格数据
            raw_dir = self.stocks_index_dir.parent / "raw"
            
            if not raw_dir.exists():
                print(f"错误: raw 目录不存在: {raw_dir}")
                return pd.DataFrame()
            
            all_stocks_data = []
            
            for _, row in index_df.iterrows():
                code = row['code']
                stock_file = raw_dir / f"{code}.csv"
                
                if not stock_file.exists():
                    continue
                
                try:
                    # 读取股票价格数据
                    stock_df = pd.read_csv(stock_file, encoding='utf-8-sig')
                    
                    # 标准化列名
                    if '日期' in stock_df.columns:
                        price_mapping = {
                            '日期': 'date',
                            '开盘': 'open',
                            '收盘': 'close',
                            '最高': 'high',
                            '最低': 'low',
                            '成交量': 'volume',
                        }
                        stock_df = stock_df.rename(columns=price_mapping)
                    
                    # 确保有必要的列
                    if 'date' not in stock_df.columns or 'close' not in stock_df.columns:
                        continue
                    
                    # 转换日期格式
                    stock_df['date'] = pd.to_datetime(stock_df['date'])
                    
                    # 筛选目标日期的数据
                    target_dt = pd.to_datetime(target_date)
                    stock_df = stock_df[stock_df['date'] == target_dt]
                    
                    if stock_df.empty:
                        continue
                    
                    # 添加股票代码和名称
                    stock_df['code'] = code
                    if 'name' in row:
                        stock_df['name'] = row['name']
                    if 'industry' in row:
                        stock_df['industry'] = row['industry']
                    
                    # 确保数值列是数值类型
                    for col in ['open', 'close', 'high', 'low', 'volume']:
                        if col in stock_df.columns:
                            stock_df[col] = pd.to_numeric(stock_df[col], errors='coerce')
                    
                    all_stocks_data.append(stock_df)
                    
                except Exception as e:
                    # 跳过有问题的股票
                    continue
            
            if not all_stocks_data:
                print(f"警告: {target_date} 没有找到任何有效的价格数据")
                return pd.DataFrame()
            
            # 合并所有股票数据
            result = pd.concat(all_stocks_data, ignore_index=True)
            
            if show_progress:
                print(f"[OK] 加载 {target_date}: {len(result)} 条有效记录")
            
            return result
            
        except Exception as e:
            print(f"错误: 加载 {target_date} 数据失败: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def load_recent_days(self, days: int, show_progress: bool = True) -> pd.DataFrame:
        """
        加载最近N天的数据
        
        Args:
            days: 天数
            show_progress: 是否显示进度条
        
        Returns:
            合并后的数据 DataFrame
        """
        available_dates = self.get_available_dates()
        
        if not available_dates:
            print("错误: 没有找到任何可用的日期数据")
            return pd.DataFrame()
        
        # 取最近N天
        recent_dates = available_dates[-days:] if len(available_dates) >= days else available_dates
        
        if show_progress:
            print(f"[数据] 加载最近 {len(recent_dates)} 天的数据...")
            print(f"[数据] 日期范围: {recent_dates[0]} 至 {recent_dates[-1]}")
        
        all_data = []
        
        with ProgressBar(len(recent_dates), desc="加载进度") as pbar:
            for date_str in recent_dates:
                df = self.load_single_date(date_str, show_progress=False)
                if not df.empty:
                    all_data.append(df)
                    pbar.update(1, success=True)
                else:
                    pbar.update(1, success=False)
        
        if not all_data:
            return pd.DataFrame()
        
        result = pd.concat(all_data, ignore_index=True)
        
        if show_progress:
            unique_dates = result['date'].nunique() if 'date' in result.columns else len(recent_dates)
            print(f"[统计] 成功加载: {len(result)} 条记录，{unique_dates} 个交易日")
        
        return result
    
    def load_latest_date(self, show_progress: bool = True) -> pd.DataFrame:
        """
        加载最新交易日的数据
        
        Args:
            show_progress: 是否显示进度条
        
        Returns:
            股票数据 DataFrame
        """
        available_dates = self.get_available_dates()
        
        if not available_dates:
            print("错误: 没有找到任何可用的日期数据")
            return pd.DataFrame()
        
        latest_date = available_dates[-1]
        
        if show_progress:
            print(f"[数据] 最新交易日: {latest_date}")
        
        return self.load_single_date(latest_date, show_progress=show_progress)
    
    def load_date_range(self, start_date: str, end_date: str, show_progress: bool = True) -> pd.DataFrame:
        """
        加载指定日期范围的数据
        
        Args:
            start_date: 开始日期，格式: '2026-01-28'
            end_date: 结束日期，格式: '2026-01-30'
            show_progress: 是否显示进度条
        
        Returns:
            合并后的数据 DataFrame
        """
        available_dates = self.get_available_dates()
        
        if not available_dates:
            print("错误: 没有找到任何可用的日期数据")
            return pd.DataFrame()
        
        # 筛选日期范围
        filtered_dates = [d for d in available_dates if start_date <= d <= end_date]
        
        if not filtered_dates:
            print(f"错误: 在 {start_date} 至 {end_date} 范围内没有找到数据")
            return pd.DataFrame()
        
        if show_progress:
            print(f"[数据] 加载日期范围: {filtered_dates[0]} 至 {filtered_dates[-1]}")
            print(f"[数据] 共 {len(filtered_dates)} 个交易日")
        
        all_data = []
        
        with ProgressBar(len(filtered_dates), desc="加载进度") as pbar:
            for date_str in filtered_dates:
                df = self.load_single_date(date_str, show_progress=False)
                if not df.empty:
                    all_data.append(df)
                    pbar.update(1, success=True)
                else:
                    pbar.update(1, success=False)
        
        if not all_data:
            return pd.DataFrame()
        
        result = pd.concat(all_data, ignore_index=True)
        
        if show_progress:
            print(f"[统计] 成功加载: {len(result)} 条记录")
        
        return result
    
    def load_all_data(self, show_progress: bool = True) -> pd.DataFrame:
        """
        加载所有可用数据
        
        Args:
            show_progress: 是否显示进度条
        
        Returns:
            合并后的数据 DataFrame
        """
        available_dates = self.get_available_dates()
        
        if not available_dates:
            print("错误: 没有找到任何可用的日期数据")
            return pd.DataFrame()
        
        if show_progress:
            print(f"[数据] 加载所有数据...")
            print(f"[数据] 日期范围: {available_dates[0]} 至 {available_dates[-1]}")
            print(f"[数据] 共 {len(available_dates)} 个交易日")
        
        all_data = []
        
        with ProgressBar(len(available_dates), desc="加载进度") as pbar:
            for date_str in available_dates:
                df = self.load_single_date(date_str, show_progress=False)
                if not df.empty:
                    all_data.append(df)
                    pbar.update(1, success=True)
                else:
                    pbar.update(1, success=False)
        
        if not all_data:
            return pd.DataFrame()
        
        result = pd.concat(all_data, ignore_index=True)
        
        if show_progress:
            unique_dates = result['date'].nunique() if 'date' in result.columns else len(available_dates)
            print(f"[统计] 成功加载: {len(result)} 条记录，{unique_dates} 个交易日")
        
        return result
    
    def calculate_previous_close(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算每只股票的前一交易日数据（收盘价、开盘价等）

        Args:
            df: 股票数据DataFrame

        Returns:
            添加了前一日数据列的DataFrame
        """
        if df.empty:
            return df

        # 确保按代码和日期排序
        df = df.sort_values(['code', 'date'])

        # 使用 groupby + shift 计算前一日数据
        df['prev_close'] = df.groupby('code')['close'].shift(1)
        df['yesterday_open'] = df.groupby('code')['open'].shift(1)
        df['yesterday_close'] = df.groupby('code')['close'].shift(1)

        return df
