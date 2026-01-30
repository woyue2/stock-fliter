# -*- coding: utf-8 -*-
"""
数据获取模块
使用 akshare 获取股票数据，实时抓取并保存到本地
"""
import time
import pandas as pd
import akshare as ak
from pathlib import Path
from datetime import datetime


class DataFetcher:
    """数据获取类"""

    def __init__(self, data_dir='./data'):
        """
        初始化

        Parameters:
        -----------
        data_dir : str
            数据保存目录
        """
        self.retry_times = 3
        self.retry_delay = 2
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_stock_list(self):
        """
        获取A股股票列表（实时抓取）

        Returns:
        --------
        dict
            {股票代码: 股票名称}
        """
        # 从网络获取
        try:
            stock_info = ak.stock_info_a_code_name()

            # 创建代码到名称的映射
            stock_dict = dict(zip(stock_info['code'], stock_info['name']))

            # 保存到本地CSV
            try:
                csv_file = self.data_dir / f'stock_list_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                stock_info.to_csv(csv_file, index=False, encoding='utf-8-sig')
                print(f"✓ 获取并保存 {len(stock_dict)} 只股票到 {csv_file.name}")
            except Exception as e:
                print(f"✓ 获取到 {len(stock_dict)} 只股票（保存失败: {e}）")

            return stock_dict

        except Exception as e:
            print(f"✗ 获取股票列表失败: {e}")
            return {}

    def get_stock_data(self, stock_code, period='daily', start_date='20200101', end_date=None, save_to_file=True):
        """
        获取单只股票的历史数据（实时抓取）

        Parameters:
        -----------
        stock_code : str
            股票代码（如 '000001'）
        period : str
            周期：'daily'(日线), 'weekly'(周线), 'monthly'(月线)
        start_date : str
            开始日期，格式 'YYYYMMDD'
        end_date : str
            结束日期，格式 'YYYYMMDD'，默认为今天
        save_to_file : bool
            是否保存到本地CSV文件

        Returns:
        --------
        pd.DataFrame or None
            股票数据，包含列：日期、开盘、收盘、最高、最低、成交量、成交额
        """
        if end_date is None:
            end_date = pd.Timestamp.now().strftime('%Y%m%d')

        for attempt in range(self.retry_times):
            try:
                # 根据周期选择不同的函数
                if period == 'daily':
                    df = ak.stock_zh_a_hist(
                        symbol=stock_code,
                        period="daily",
                        start_date=start_date,
                        end_date=end_date,
                        adjust="qfq"  # 前复权
                    )
                elif period == 'weekly':
                    df = ak.stock_zh_a_hist(
                        symbol=stock_code,
                        period="weekly",
                        start_date=start_date,
                        end_date=end_date,
                        adjust="qfq"
                    )
                elif period == 'monthly':
                    df = ak.stock_zh_a_hist(
                        symbol=stock_code,
                        period="monthly",
                        start_date=start_date,
                        end_date=end_date,
                        adjust="qfq"
                    )
                else:
                    print(f"✗ 不支持的周期: {period}")
                    return None

                if df is not None and len(df) > 0:
                    # 重命名列（统一命名）
                    df = df.rename(columns={
                        '日期': 'date',
                        '开盘': 'open',
                        '收盘': 'close',
                        '最高': 'high',
                        '最低': 'low',
                        '成交量': 'volume',
                        '成交额': 'amount',
                        '振幅': 'amplitude',
                        '涨跌幅': 'change_pct',
                        '涨跌额': 'change_amount',
                        '换手率': 'turnover'
                    })

                    # 确保日期是datetime格式
                    df['date'] = pd.to_datetime(df['date'])

                    # 保存到本地CSV
                    if save_to_file:
                        try:
                            csv_file = self.data_dir / f"{stock_code}_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                            print(f"✓ 获取并保存 {stock_code} 数据到 {csv_file.name}")
                        except Exception as e:
                            print(f"✓ 获取 {stock_code} 数据（保存失败: {e}）")
                    else:
                        print(f"✓ 获取 {stock_code} 数据")

                    return df
                else:
                    return None

            except Exception as e:
                if attempt < self.retry_times - 1:
                    print(f"⚠ 获取 {stock_code} 数据失败，重试中... ({attempt + 1}/{self.retry_times})")
                    time.sleep(self.retry_delay)
                else:
                    print(f"✗ 获取 {stock_code} 数据失败: {e}")
                    return None

        return None

    def get_stock_data_for_analysis(self, stock_code, days_needed=60, save_to_file=True):
        """
        获取足够用于分析的数据（实时抓取）

        Parameters:
        -----------
        stock_code : str
            股票代码
        days_needed : int
            需要的交易天数
        save_to_file : bool
            是否保存到本地CSV文件

        Returns:
        --------
        pd.DataFrame or None
            股票数据
        """
        # 实时从网络获取
        start_date = (pd.Timestamp.now() - pd.Timedelta(days=days_needed * 2)).strftime('%Y%m%d')
        df = self.get_stock_data(stock_code, start_date=start_date, save_to_file=save_to_file)

        if df is not None and len(df) >= days_needed:
            return df
        else:
            return None

    def batch_get_stock_data(self, stock_list, days_needed=60, progress_callback=None):
        """
        批量获取股票数据

        Parameters:
        -----------
        stock_list : list
            股票代码列表
        days_needed : int
            需要的交易天数
        progress_callback : function
            进度回调函数

        Returns:
        --------
        dict
            {股票代码: DataFrame}
        """
        stock_data_dict = {}

        for i, stock_code in enumerate(stock_list):
            df = self.get_stock_data_for_analysis(stock_code, days_needed)

            if df is not None:
                stock_data_dict[stock_code] = df

            # 调用进度回调
            if progress_callback:
                progress_callback(i + 1, len(stock_list), stock_code)

            # 避免请求过快
            time.sleep(0.1)

        return stock_data_dict
