# -*- coding: utf-8 -*-
"""
A股数据获取模块
获取日K、周K、月K数据
"""
import time
from pathlib import Path
from typing import Optional, Tuple
import warnings

import akshare as ak
import pandas as pd

warnings.filterwarnings("ignore")


class StockDataFetcher:
    """股票数据获取器"""

    def __init__(self, cache_dir: str = "./data"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_stock_list(self) -> pd.DataFrame:
        """
        获取A股股票列表

        返回:
            股票列表DataFrame，包含代码、名称、最新价、市值等
        """
        max_retries = 3
        backoff = 2

        for attempt in range(1, max_retries + 1):
            try:
                print("[数据] 正在获取A股股票列表...")
                stock_list = ak.stock_zh_a_spot_em()

                if stock_list is None or len(stock_list) == 0:
                    raise ValueError("接口返回空数据")

                keep_cols = ["代码", "名称", "最新价", "总市值", "流通市值"]
                missing = [col for col in keep_cols if col not in stock_list.columns]
                if missing:
                    raise KeyError(f"缺少字段: {missing}")

                stock_list = stock_list[keep_cols]
                stock_list.columns = ["code", "name", "price", "market_cap", "float_cap"]

                print(f"[OK] 共获取到 {len(stock_list)} 只A股")
                return stock_list

            except Exception as e:
                print(f"[X] 获取股票列表失败: {e}")
                if attempt < max_retries:
                    sleep_seconds = backoff**attempt
                    print(f"[数据] {sleep_seconds} 秒后重试 ({attempt}/{max_retries})...")
                    time.sleep(sleep_seconds)

        # 备用接口，仅返回代码/名称
        try:
            print("[数据] 尝试使用备用接口获取代码列表...")
            alt = ak.stock_info_a_code_name()

            if alt is None or len(alt) == 0:
                raise ValueError("备用接口返回空数据")

            if {"code", "name"}.issubset(alt.columns):
                alt = alt[["code", "name"]]
            elif {"代码", "名称"}.issubset(alt.columns):
                alt = alt[["代码", "名称"]]
                alt.columns = ["code", "name"]
            else:
                raise KeyError(f"备用接口字段未知: {list(alt.columns)}")

            alt["price"] = pd.NA
            alt["market_cap"] = pd.NA
            alt["float_cap"] = pd.NA

            print(f"[OK] 备用接口获取到 {len(alt)} 只股票（无市值/价格）")
            return alt

        except Exception as e:
            print(f"[X] 备用接口也失败: {e}")
            return pd.DataFrame()

    def get_daily_k(self, code: str, period: str = "daily", adjust: str = "qfq") -> Optional[pd.DataFrame]:
        """
        获取K线数据（日K/周K/月K）

        参数:
            code: 股票代码
            period: 周期 - daily(日K), weekly(周K), monthly(月K)
            adjust: 复权方式 - qfq(前复权), hfq(后复权), ''(不复权)

        返回:
            K线DataFrame
        """
        max_retries = 3
        backoff = 2

        for attempt in range(1, max_retries + 1):
            try:
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period=period,
                    start_date="19900101",
                    adjust=adjust if period == "daily" else "",
                )

                if df is None or len(df) == 0:
                    return None

                keep_cols = ["日期", "开盘", "最高", "最低", "收盘", "成交量"]
                if not set(keep_cols).issubset(df.columns):
                    raise KeyError(f"字段缺失: {keep_cols}")

                df = df[keep_cols]
                df.columns = ["date", "open", "high", "low", "close", "volume"]
                df["date"] = pd.to_datetime(df["date"])
                df.set_index("date", inplace=True)

                return df

            except Exception as e:
                print(f"[!] 获取 {code} {period} 数据失败: {e}")
                if attempt < max_retries:
                    sleep_seconds = backoff**attempt
                    print(f"[数据] {sleep_seconds} 秒后重试 ({attempt}/{max_retries})...")
                    time.sleep(sleep_seconds)

        return None

    def get_multi_period_data(
        self, code: str
    ) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """
        获取单只股票的三个周期数据

        参数:
            code: 股票代码

        返回:
            (日K, 周K, 月K) 三个DataFrame
        """
        daily_df = self.get_daily_k(code, period="daily", adjust="qfq")

        if daily_df is None or len(daily_df) < 50:
            return None, None, None

        try:
            weekly_df = self._resample_ohlcv(daily_df, "W")
            monthly_df = self._resample_ohlcv(daily_df, "M")
            return daily_df, weekly_df, monthly_df

        except Exception as e:
            print(f"[!] 生成 {code} 周K/月K 失败: {e}")
            return daily_df, None, None

    def _resample_ohlcv(self, df: pd.DataFrame, freq: str) -> pd.DataFrame:
        """
        将日K重采样为周K或月K

        参数:
            df: 日K DataFrame
            freq: 'W'=周, 'M'=月

        返回:
            重采样后的DataFrame
        """
        resampled = df.resample(freq).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )

        resampled = resampled.dropna()
        return resampled

    def save_to_cache(
        self, code: str, daily_df: pd.DataFrame, weekly_df: pd.DataFrame, monthly_df: pd.DataFrame
    ):
        """保存数据到缓存"""
        try:
            cache_file = self.cache_dir / f"{code}.pkl"
            data = {
                "daily": daily_df,
                "weekly": weekly_df,
                "monthly": monthly_df,
                "update_time": pd.Timestamp.now(),
            }
            pd.to_pickle(data, cache_file)
        except Exception as e:
            print(f"[!] 缓存 {code} 失败: {e}")

    def load_from_cache(self, code: str, max_age_days: int = 1) -> Optional[dict]:
        """
        从缓存加载数据

        参数:
            code: 股票代码
            max_age_days: 缓存最大有效期（天）

        返回:
            数据字典或None
        """
        try:
            cache_file = self.cache_dir / f"{code}.pkl"

            if not cache_file.exists():
                return None

            data = pd.read_pickle(cache_file)
            update_time = data.get("update_time")

            if update_time and (pd.Timestamp.now() - update_time).days > max_age_days:
                return None

            return data

        except Exception as e:
            print(f"[!] 加载 {code} 缓存失败: {e}")
            return None


if __name__ == "__main__":
    fetcher = StockDataFetcher()

    stock_list = fetcher.get_stock_list()
    print(stock_list.head(10))

    if len(stock_list) > 0:
        test_code = stock_list.iloc[0]["code"]
        print(f"\n📈 测试获取 {test_code} 数据...")

        daily, weekly, monthly = fetcher.get_multi_period_data(test_code)

        if daily is not None:
            print(f"日K: {len(daily)} 条")
            print(f"周K: {len(weekly)} 条")
            print(f"月K: {len(monthly)} 条")
            print("\n日K最近5条")
            print(daily.tail())
