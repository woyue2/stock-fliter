# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  Limit, Min bars, horizons
# OUTPUT: pd.DataFrame with trend signal results
# POS:    check-maxrsix6u1d/analyzers/trend_analyzer.py
# -*- coding: utf-8 -*-
"""
趋势分析器

包含三种趋势规则：
1. 趋势跟随（trend_follow）
2. 上升趋势中的回撤（pullback_in_uptrend）
3. 波动收缩突破（volatility_contraction_breakout）

同时计算玄学指标（可选）
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from data_loader import iter_stock_items, load_daily_data
from indicators_6u1d import compute_all_6u1d_indicators, PATTERN_6U1D_COLUMN_MAP
from indicators_6u1d_fuzzy import (
    compute_all_6u1d_indicators_fuzzy,
    PATTERN_6U1D_FUZZY_COLUMN_MAP,
    DEFAULT_SMALL_DROP_THRESHOLD
)

try:
    from tqdm import tqdm
    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0) -> Dict[str, pd.Series]:
    mid = sma(series, window)
    std = series.rolling(window=window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    bandwidth = (upper - lower) / mid
    return {"mid": mid, "upper": upper, "lower": lower, "bandwidth": bandwidth}


def volume_ratio(volumes: pd.Series, window: int = 20) -> pd.Series:
    return volumes / volumes.rolling(window=window).mean()


def rule_trend_follow(df: pd.DataFrame) -> pd.Series:
    """趋势跟随规则"""
    close = df["close"].astype(float)
    ma20 = sma(close, 20)
    ma60 = sma(close, 60)
    slope20 = ma20 - ma20.shift(5)
    slope60 = ma60 - ma60.shift(10)
    return (ma20 > ma60) & (slope20 > 0) & (slope60 > 0) & (close > ma20)


def rule_pullback_in_uptrend(df: pd.DataFrame) -> pd.Series:
    """上升趋势中的回撤规则"""
    close = df["close"].astype(float)
    ma20 = sma(close, 20)
    ma60 = sma(close, 60)
    slope60 = ma60 - ma60.shift(10)
    rsi14 = rsi(close, 14)
    pullback = (close < ma20) & (close > ma60 * 0.98)
    rsi_ok = (rsi14 >= 40) & (rsi14 <= 55)
    return (ma20 > ma60) & (slope60 > 0) & pullback & rsi_ok


def rule_volatility_contraction_breakout(
    df: pd.DataFrame,
    bb_window: int = 20,
    num_std: float = 2.0,
    quantile: float = 0.2,
    quantile_window: int = 120,
    vol_ratio_threshold: float = 1.8,
) -> pd.Series:
    """波动收缩突破规则"""
    close = df["close"].astype(float)
    vols = df["volume"].astype(float)
    ma60 = sma(close, 60)
    ma20 = sma(close, 20)
    slope60 = ma60 - ma60.shift(10)
    rsi14 = rsi(close, 14)
    bb = bollinger_bands(close, bb_window, num_std)
    bandwidth = bb["bandwidth"]
    vol_ratio = volume_ratio(vols, 20)

    low_vol = bandwidth <= bandwidth.rolling(quantile_window).quantile(quantile)
    breakout = close > bb["upper"]
    vol_confirm = vol_ratio >= vol_ratio_threshold
    trend_filter = (close > ma60) & (ma20 > ma60) & (slope60 > 0)
    momentum_filter = (close > close.shift(5)) & (rsi14 >= 50) & (rsi14 <= 70)
    return low_vol & breakout & vol_confirm & trend_filter & momentum_filter


def get_board_type(code: str) -> str:
    """获取板块类型"""
    if code.startswith('688'):
        return '科创板'
    if code.startswith('300') or code.startswith('301'):
        return '创业板'
    if code.startswith('8'):
        return '北交所'
    if code.startswith('002') or code.startswith('000'):
        return '深圳主板'
    if code.startswith('60'):
        return '上海主板'
    return '其他'


def load_industry_map() -> Dict[str, str]:
    """加载行业映射"""
    # 已废弃，改用 StockItem.industry
    return {}


class TrendAnalyzer:
    """趋势分析器"""
    
    def __init__(
        self,
        limit: Optional[int] = None,
        output_dir: Optional[Path] = None,
        include_mystic: bool = True,
        lookback_days: int = 120,
        min_bars: int = 120,
        horizons: Optional[List[int]] = None,
        end_date: Optional[str] = None
    ):
        self.limit = limit
        self.output_dir = output_dir or Path(__file__).resolve().parent.parent / "output"
        self.include_mystic = include_mystic
        self.lookback_days = lookback_days
        self.min_bars = min_bars
        self.horizons = horizons or [5, 20, 60]
        self.end_date = end_date
    
    def run(self) -> tuple[pd.DataFrame, Optional[datetime]]:
        """运行分析，返回结果DataFrame和数据最新日期"""
        results = []
        global_max_date = None  # 存储所有股票数据中的最新日期

        items = list(iter_stock_items(limit=self.limit))
        iterator = tqdm(items, desc="趋势分析") if _HAS_TQDM else items

        for item in iterator:
            df = load_daily_data(item.code)

            if df.empty:
                continue

            # Filter by end_date if provided
            if self.end_date:
                df["date"] = pd.to_datetime(df["date"])
                df = df[df["date"] <= self.end_date]
            else:
                # 记录数据最新日期
                df["date"] = pd.to_datetime(df["date"])
                latest_date = df["date"].max()
                if global_max_date is None or latest_date > global_max_date:
                    global_max_date = latest_date

            if len(df) < self.min_bars:
                continue

            result = self._analyze_stock(item.code, item.name, item.industry, df)
            if result:
                results.append(result)

        result_df = pd.DataFrame(results)

        # 重命名6U1D列为中文名
        if not result_df.empty:
            result_df = self._rename_pattern_columns(result_df)

        # 保存结果
        if self.output_dir:
            self._save_results(result_df)

        # 打印数据最新日期
        if global_max_date:
            print(f"[MAxRSIx6U1D分析] 数据最新日期: {global_max_date.strftime('%Y-%m-%d')}")

        return result_df, global_max_date
    
    def _analyze_stock(self, code: str, name: str, industry: str, df: pd.DataFrame) -> Optional[Dict]:
        """分析单只股票"""
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.reset_index(drop=True)
        
        last_date = df["date"].iloc[-1]
        cutoff = last_date - pd.Timedelta(days=self.lookback_days)
        
        # 计算规则信号
        df["trend_follow"] = rule_trend_follow(df)
        df["pullback_in_uptrend"] = rule_pullback_in_uptrend(df)
        df["vol_contraction_breakout"] = rule_volatility_contraction_breakout(df)
        
        df_recent = df[df["date"] >= cutoff]
        close_series = df["close"].astype(float)
        open_series = df["open"].astype(float) if "open" in df.columns else None
        
        result = {
            "代码": code,
            "名称": name,
            "板块": get_board_type(code),
            "行业": industry,
            "最新日期": last_date.strftime("%Y-%m-%d"),
            "最新价": float(close_series.iloc[-1]),
        }
        
        # 6U1D指标（原版：严格6连阳）
        if self.include_mystic and open_series is not None:
            pattern_results = compute_all_6u1d_indicators(open_series, close_series, lookback_days=10)
            result.update(pattern_results)
            
            # 6U1D指标（模糊版：允许小跌）
            fuzzy_results = compute_all_6u1d_indicators_fuzzy(
                open_series, close_series, lookback_days=10, small_drop_threshold=DEFAULT_SMALL_DROP_THRESHOLD
            )
            result.update(fuzzy_results)
        
        # 趋势规则信号
        for rule, cn_name in [
            ("trend_follow", "趋势跟随"),
            ("pullback_in_uptrend", "上升回撤"),
            ("vol_contraction_breakout", "波动收缩突破")
        ]:
            signals = df_recent[df_recent[rule] == True]
            has_signal = not signals.empty
            result[f"{cn_name}_是否信号"] = has_signal
            
            if has_signal:
                last_signal = signals.iloc[-1]
                result[f"{cn_name}_信号日期"] = last_signal["date"].strftime("%Y-%m-%d")
                result[f"{cn_name}_信号价格"] = float(last_signal["close"])
        
        return result
    
    def _rename_pattern_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """将6U1D列重命名为中文"""
        rename_map = {}
        # 原版6U1D指标
        for eng_name, cn_name in PATTERN_6U1D_COLUMN_MAP.items():
            if eng_name in df.columns:
                rename_map[eng_name] = cn_name
        # 模糊版6U1D指标
        for eng_name, cn_name in PATTERN_6U1D_FUZZY_COLUMN_MAP.items():
            if eng_name in df.columns:
                rename_map[eng_name] = cn_name
        return df.rename(columns=rename_map)
    
    def _save_results(self, df: pd.DataFrame):
        """保存分析结果"""
        now = datetime.now()
        ts = now.strftime("%Y%m%d_%H%M%S")
        
        # 详细结果
        detail_path = self.output_dir / f"trend_rules_detail_{ts}.csv"
        df.to_csv(detail_path, index=False, encoding="utf-8-sig")
        print(f"  [OK] 趋势分析详情: {detail_path.name} ({len(df)} 只)")
        
        # 汇总统计
        summary = self._compute_summary(df)
        summary_path = self.output_dir / f"trend_rules_summary_{ts}.csv"
        summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
        print(f"  [OK] 趋势分析汇总: {summary_path.name}")
        
        # 保存6U1D候选（满足任一6U1D条件的股票）
        pattern_cols = [c for c in df.columns if c.startswith("6U1D_") or c.startswith("6U1D模糊_")]
        if pattern_cols:
            pattern_mask = df[pattern_cols].any(axis=1)
            pattern_df = df[pattern_mask].copy()
            pattern_path = self.output_dir / f"momentum_6u1d_candidates_{ts}.csv"
            pattern_df.to_csv(pattern_path, index=False, encoding="utf-8-sig")
            print(f"  [OK] 6U1D 候选: {pattern_path.name} ({len(pattern_df)} 只)")
    
    def _compute_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算汇总统计"""
        rows = []
        
        # 趋势规则统计
        for cn_name in ["趋势跟随", "上升回撤", "波动收缩突破"]:
            col = f"{cn_name}_是否信号"
            if col in df.columns:
                signal_count = df[col].sum()
                rows.append({
                    "规则": cn_name,
                    "信号数量": signal_count,
                    "占比": f"{signal_count / len(df) * 100:.1f}%" if len(df) > 0 else "0%"
                })
        
        # 6U1D 指标统计
        pattern_cols = [c for c in df.columns if c.startswith("6U1D_") or c.startswith("6U1D模糊_")]
        for col in pattern_cols:
            signal_count = df[col].sum()
            rows.append({
                "规则": col,
                "信号数量": signal_count,
                "占比": f"{signal_count / len(df) * 100:.1f}%" if len(df) > 0 else "0%"
            })
        
        return pd.DataFrame(rows)
