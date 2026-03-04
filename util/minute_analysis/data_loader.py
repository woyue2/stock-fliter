# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  Path — 分钟数据目录 (data_dir)
# OUTPUT: List[Dict] — 股票分钟数据（code/name/data/returns）
# POS:    util/minute_analysis/data_loader.py（迁移自 check-market-sentiment/sentiment_analyzer/）
"""
Data Loader Module
加载全市场分钟数据
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    """分钟数据加载器"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Args:
            data_dir: 分钟数据根目录 (默认: ~/Park/stock-fliter/get-data/data/minute_akshare)
        """
        self.data_dir = data_dir or Path.home() / \
            "Park/stock-fliter/get-data/data/minute_akshare"
    
    def get_available_dates(self) -> List[str]:
        """获取可用的日期列表"""
        if not self.data_dir.exists():
            logger.warning(f"Data directory not found: {self.data_dir}")
            return []
        
        dates = set()
        
        # 检查子目录（格式: YYYY-MM-DD）
        for date_dir in self.data_dir.iterdir():
            if date_dir.is_dir() and date_dir.name.count('-') == 2:
                try:
                    from datetime import datetime
                    datetime.strptime(date_dir.name, '%Y-%m-%d')
                    dates.add(date_dir.name)
                except ValueError:
                    continue
        
        # 检查CSV文件中的日期（根目录的CSV可能有不同日期）
        for csv_file in self.data_dir.glob("*.csv"):
            try:
                df = pd.read_csv(csv_file, nrows=1)
                if 'date' in df.columns:
                    file_date = df['date'].iloc[0]
                    if isinstance(file_date, str) and file_date.count('-') == 2:
                        dates.add(file_date)
            except Exception:
                continue
        
        return sorted(dates)
    
    def get_latest_date(self) -> Optional[str]:
        """获取最新的可用日期"""
        dates = self.get_available_dates()
        return dates[-1] if dates else None
    
    def load_stock_minute_data(self, file_path: Path) -> Optional[Dict]:
        """
        加载单只股票的分钟数据
        
        Returns:
            Dict with keys:
                - code: 股票代码
                - name: 股票名称 (从文件名解析)
                - data: DataFrame with columns [time, open, high, low, close, volume, amount]
                - returns: 日内收益率 Series
        """
        try:
            df = pd.read_csv(file_path)
            
            # 支持多种列名格式
            # 格式1: datetime, open, high, low, close, volume, code, date
            # 格式2: time, open, high, low, close, volume, amount
            
            # 统一列名 (先转换)
            column_mapping = {
                'datetime': 'time',
            }
            df = df.rename(columns=column_mapping)
            
            # 确保必要的列存在
            required_cols = ['time', 'open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                logger.warning(f"Missing columns in {file_path.name}: {list(df.columns)}")
                return None
            
            # 计算日内收益率
            df['return'] = (df['close'] - df['open']) / df['open']
            
            # 解析股票代码和名称
            code = file_path.stem
            
            # 估算股票名称 (从文件名的市场前缀判断)
            name_map = {
                '6': '沪市',
                '0': '深市',
                '3': '创业板',
                '8': '科创板'
            }
            market = name_map.get(code[0], '未知')
            
            return {
                'code': code,
                'name': f"{market}{code}",
                'data': df,
                'returns': df['return']
            }
            
        except Exception as e:
            logger.error(f"Error loading {file_path.name}: {e}")
            return None
    
    def load_all_stocks(self, date: str, 
                        sample: Optional[int] = None,
                        show_progress: bool = True) -> List[Dict]:
        """
        加载指定日期的所有股票分钟数据
        
        Args:
            date: 日期字符串 (YYYY-MM-DD)
            sample: 采样数量 (None表示加载全部)
            show_progress: 显示进度
        
        Returns:
            股票数据列表
        """
        csv_files = []
        target_date = date
        
        # 优先从子目录加载
        date_dir = self.data_dir / date
        if date_dir.exists():
            csv_files = list(date_dir.glob("*.csv"))
            if show_progress:
                logger.info(f"从子目录加载: {len(csv_files)} 只股票")
        
        # 如果子目录文件太少或不存在，从根目录加载所有CSV
        if not csv_files or (sample and len(csv_files) < sample):
            csv_files = []
            for csv_file in self.data_dir.glob("*.csv"):
                try:
                    df = pd.read_csv(csv_file, nrows=1)
                    if 'date' in df.columns:
                        file_date = df['date'].iloc[0]
                        if file_date == target_date:
                            csv_files.append(csv_file)
                    else:
                        # 没有日期列的也加上（默认使用）
                        csv_files.append(csv_file)
                except Exception:
                    continue
            
            if show_progress:
                logger.info(f"从根目录加载: {len(csv_files)} 只股票")
        
        if not csv_files:
            logger.error(f"No CSV files found for date: {date}")
            return []
        
        # 采样
        if sample:
            import random
            csv_files = random.sample(csv_files, min(sample, len(csv_files)))
        
        if show_progress:
            logger.info(f"Loading {len(csv_files)} stocks for {date}...")
        
        # 并行加载
        results = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(self.load_stock_minute_data, f): f 
                      for f in csv_files}
            
            for i, future in enumerate(futures):
                result = future.result()
                if result:
                    results.append(result)
                
                if show_progress and (i + 1) % 500 == 0:
                    logger.info(f"Loaded {i + 1}/{len(csv_files)} stocks...")
        
        logger.info(f"Successfully loaded {len(results)} stocks")
        return results
    
    def calculate_market_statistics(self, stocks: List[Dict]) -> Dict:
        """
        计算全市场基础统计
        
        Args:
            stocks: 股票数据列表
        
        Returns:
            市场统计数据
        """
        if not stocks:
            return {}
        
        returns = [s['returns'].iloc[-1] for s in stocks]
        volumes = []
        for s in stocks:
            if 'volume' in s['data'].columns:
                volumes.append(s['data']['volume'].sum())
        
        return {
            'total_stocks': len(stocks),
            'avg_return': np.mean(returns),
            'median_return': np.median(returns),
            'std_return': np.std(returns),
            'up_count': sum(1 for r in returns if r > 0),
            'down_count': sum(1 for r in returns if r < 0),
            'flat_count': sum(1 for r in returns if r == 0),
            'up_down_ratio': sum(1 for r in returns if r > 0) / max(1, sum(1 for r in returns if r < 0)),
            'total_volume': sum(volumes) if volumes else 0,
            'positive_ratio': sum(1 for r in returns if r > 0) / len(returns)
        }
