# -*- coding: utf-8 -*-
"""
多规则趋势分析脚本（仅本地数据）

规则类别：
1) 趋势跟随（trend_follow）
2) 上升趋势中的回撤（pullback_in_uptrend）
3) 波动收缩突破（volatility_contraction_breakout）

输出：
- output/trend_rules_detail_YYYYMMDD_HHMMSS.csv
- output/trend_rules_summary_YYYYMMDD_HHMMSS.csv
- output/trend_rules_report_YYYYMMDD_HHMMSS.md
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd

from data_loader import iter_stock_items, load_daily_data, load_selected_stocks
from mystic_indicators import (
    mystic_6up1down_in_window,
    mystic_consecutive_6up,
    mystic_today_down_after_6up,
    mystic_today_is_6th_up,
    mystic_6up_prev_down,
    compute_all_mystic_indicators,
    MYSTIC_COLUMN_MAP,
)

try:
    from tqdm import tqdm
    _HAS_TQDM = True
except Exception:
    _HAS_TQDM = False


@dataclass
class RuleConfig:
    name: str
    lookback_days: int


@dataclass
class TrendRulesConfig:
    lookback_days: int = 120
    min_bars: int = 120
    horizons: List[int] = None

    def __post_init__(self):
        if self.horizons is None:
            self.horizons = [5, 20, 60]


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


# 玄学指标现在统一从 mystic_indicators 模块导入
# 保留别名以兼容旧代码
def has_mystic_pattern(open_series: pd.Series, close_series: pd.Series, lookback_days: int = 10) -> bool:
    """兼容别名：10天窗口内有6连阳后1阴"""
    return mystic_6up1down_in_window(open_series, close_series, lookback_days)


def mystic_6up_6d(open_series: pd.Series, close_series: pd.Series) -> bool:
    """兼容别名：最近6天连续阳线"""
    return mystic_consecutive_6up(open_series, close_series)


def load_industry_map() -> Dict[str, str]:
    base_dir = Path(__file__).resolve().parent.parent / "just-stock-down"
    output_dir = base_dir / "output"
    data_dir = base_dir / "data"

    files = sorted(output_dir.glob("analysis_summary_*.csv"), reverse=True)
    if not files:
        files = sorted(data_dir.glob("analysis_summary_*.csv"), reverse=True)
    if not files:
        return {}

    path = files[0]
    header = pd.read_csv(path, nrows=1).columns

    code_col = None
    industry_col = None
    for candidate in ["code", "股票代码"]:
        if candidate in header:
            code_col = candidate
            break
    for candidate in ["industry", "行业"]:
        if candidate in header:
            industry_col = candidate
            break

    if not code_col or not industry_col:
        return {}

    df = pd.read_csv(path, usecols=[code_col, industry_col])
    return dict(zip(df[code_col].astype(str), df[industry_col].astype(str)))


def get_board_type(code: str) -> str:
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


def bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0) -> Dict[str, pd.Series]:
    mid = sma(series, window)
    std = series.rolling(window=window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    bandwidth = (upper - lower) / mid
    return {"mid": mid, "upper": upper, "lower": lower, "bandwidth": bandwidth}


def volume_ratio(volumes: pd.Series, window: int = 20) -> pd.Series:
    return volumes / volumes.rolling(window=window).mean()


def compute_forward_returns(close: pd.Series, index: int, horizons: List[int]) -> Dict[int, float | None]:
    results: Dict[int, float | None] = {}
    for h in horizons:
        if index + h < len(close):
            base = close.iloc[index]
            future = close.iloc[index + h]
            if base and not pd.isna(base) and not pd.isna(future):
                results[h] = float((future / base) - 1.0)
            else:
                results[h] = None
        else:
            results[h] = None
    return results


def compute_latest_return(close: pd.Series, bars: int) -> float | None:
    if len(close) <= bars:
        return None
    base = close.iloc[-1 - bars]
    latest = close.iloc[-1]
    if pd.isna(base) or pd.isna(latest) or base == 0:
        return None
    return float(latest / base - 1.0)


def rule_trend_follow(df: pd.DataFrame) -> pd.Series:
    close = df["close"].astype(float)
    ma20 = sma(close, 20)
    ma60 = sma(close, 60)
    slope20 = ma20 - ma20.shift(5)
    slope60 = ma60 - ma60.shift(10)
    return (ma20 > ma60) & (slope20 > 0) & (slope60 > 0) & (close > ma20)


def rule_pullback_in_uptrend(df: pd.DataFrame) -> pd.Series:
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


def evaluate_rules(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["trend_follow"] = rule_trend_follow(df)
    df["pullback_in_uptrend"] = rule_pullback_in_uptrend(df)
    df["vol_contraction_breakout"] = rule_volatility_contraction_breakout(df)
    return df


def analyze_stock(df: pd.DataFrame, lookback_days: int, horizons: List[int]) -> Dict[str, object]:
    if df.empty:
        return {"status": "数据不足"}

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.reset_index(drop=True)

    last_date = df["date"].iloc[-1]
    cutoff = last_date - pd.Timedelta(days=lookback_days)

    df_eval = evaluate_rules(df)
    df_recent = df_eval[df_eval["date"] >= cutoff]

    latest_idx = len(df_eval) - 1

    close_series = df["close"].astype(float)
    open_series = df["open"].astype(float) if "open" in df.columns else None
    
    # 使用统一的玄学指标计算
    mystic_results = compute_all_mystic_indicators(open_series, close_series, lookback_days=10)
    
    result = {
        "latest_date": last_date.strftime("%Y-%m-%d"),
        "latest_close": float(close_series.iloc[-1]),
        "status": "近期无信号",
        "ret_60d": compute_latest_return(close_series, 60),
        # 玄学指标（使用新字段名）
        "mystic_6up1down_10d": mystic_results["mystic_6up1down_10d"],
        "mystic_consecutive_6up": mystic_results["mystic_consecutive_6up"],
        "mystic_today_down_after_6up": mystic_results["mystic_today_down_after_6up"],
        "mystic_today_is_6th_up": mystic_results["mystic_today_is_6th_up"],
        "mystic_6up_prev_down": mystic_results["mystic_6up_prev_down"],
    }

    for rule in ["trend_follow", "pullback_in_uptrend", "vol_contraction_breakout"]:
        signals = df_recent[df_recent[rule] == True]
        if not signals.empty:
            last_signal = signals.iloc[-1]
            idx = int(last_signal.name)
            returns = compute_forward_returns(close_series, idx, horizons)
            result[f"{rule}_signal"] = True
            result[f"{rule}_date"] = last_signal["date"].strftime("%Y-%m-%d")
            result[f"{rule}_close"] = float(last_signal["close"])
            for h, val in returns.items():
                result[f"{rule}_ret_{h}"] = val
        else:
            result[f"{rule}_signal"] = False

    if any(result.get(f"{r}_signal") for r in ["trend_follow", "pullback_in_uptrend", "vol_contraction_breakout"]):
        result["status"] = "有信号"

    return result


def summarize_results(df: pd.DataFrame, horizons: List[int]) -> pd.DataFrame:
    rows = []
    for rule in ["trend_follow", "pullback_in_uptrend", "vol_contraction_breakout"]:
        rule_df = df[df[f"{rule}_signal"] == True].copy()
        for h in horizons:
            col = f"{rule}_ret_{h}"
            if col not in rule_df.columns:
                valid = pd.DataFrame()
            else:
                valid = rule_df[rule_df[col].notna()]
            if valid.empty:
                rows.append({
                    "rule": rule,
                    "horizon": h,
                    "count": 0,
                    "hit_rate": None,
                    "avg_return": None,
                })
                continue
            rows.append({
                "rule": rule,
                "horizon": h,
                "count": int(len(valid)),
                "hit_rate": float((valid[col] > 0).mean()),
                "avg_return": float(valid[col].mean()),
            })
    return pd.DataFrame(rows)


def build_report(df_detail: pd.DataFrame, df_summary: pd.DataFrame, config: TrendRulesConfig) -> str:
    rule_labels = {
        "trend_follow": "趋势跟随",
        "pullback_in_uptrend": "上升回撤",
        "vol_contraction_breakout": "波动收缩突破",
    }

    def _rule_label(rule_name: str) -> str:
        if rule_name.endswith("_industry_up"):
            base = rule_name.replace("_industry_up", "")
            return f"{rule_labels.get(base, base)}（行业上行对齐）"
        return rule_labels.get(rule_name, rule_name)

    def _pct(val: float | None) -> str:
        if val is None or pd.isna(val):
            return "-"
        return f"{val:.2%}"

    def _num(val: float | None, digits: int = 2) -> str:
        if val is None or pd.isna(val):
            return "-"
        return f"{val:.{digits}f}"

    def _format_summary_table(summary_df: pd.DataFrame) -> str:
        df = summary_df.copy()
        df["rule"] = df["rule"].map(_rule_label)
        df = df.rename(columns={
            "rule": "策略",
            "horizon": "周期(天)",
            "count": "样本数",
            "hit_rate": "胜率",
            "avg_return": "平均收益",
        })
        df["胜率"] = df["胜率"].map(_pct)
        df["平均收益"] = df["平均收益"].map(_pct)
        return df.to_markdown(index=False)

    def _format_board_table(board_df: pd.DataFrame) -> str:
        board_counts = board_df["board"].value_counts().reset_index()
        board_counts.columns = ["板块", "数量"]
        board_counts["占比"] = board_counts["数量"] / board_counts["数量"].sum()
        board_counts["占比"] = board_counts["占比"].map(_pct)
        return board_counts.to_markdown(index=False)

    def _format_industry_compare(df: pd.DataFrame) -> str:
        summary = (
            df.groupby(["industry_up", "stock_up"]).size().reset_index(name="数量")
        )
        summary["占比"] = summary["数量"] / summary["数量"].sum()
        summary["行业上行"] = summary["industry_up"].map(lambda x: "是" if x else "否")
        summary["个股上行"] = summary["stock_up"].map(lambda x: "是" if x else "否")
        summary["占比"] = summary["占比"].map(_pct)
        summary = summary[["行业上行", "个股上行", "数量", "占比"]]
        return summary.to_markdown(index=False)

    def _format_coverage_table(vdf: pd.DataFrame) -> str:
        coverage = []
        for h in config.horizons:
            col = f"vol_contraction_breakout_ret_{h}"
            if col in vdf.columns:
                coverage.append({
                    "周期(天)": h,
                    "样本数": int(vdf[col].notna().sum()),
                    "占比": float(vdf[col].notna().mean()),
                })
        df_cov = pd.DataFrame(coverage)
        df_cov["占比"] = df_cov["占比"].map(_pct)
        return df_cov.to_markdown(index=False)

    def _format_detail_section(detail_df: pd.DataFrame, limit: int = 200) -> List[str]:
        lines_local = []
        detail_df = detail_df.head(limit).copy()
        for row in detail_df.itertuples(index=False):
            code = getattr(row, "code", "")
            name = getattr(row, "name", "")
            board = getattr(row, "board", "") or "未知板块"
            industry = getattr(row, "industry", "") or "未知行业"
            latest_date = getattr(row, "latest_date", "")
            latest_close = _num(getattr(row, "latest_close", None), 2)
            status = getattr(row, "status", "")
            lines_local.append(f"### {code} {name}（{board}）")
            lines_local.append(f"- 行业: {industry}")
            lines_local.append(f"- 最新日期: {latest_date} | 最新价: {latest_close} | 状态: {status}")

            ret_60d = getattr(row, "ret_60d", None)
            if ret_60d is not None and not pd.isna(ret_60d):
                lines_local.append(f"- 近60日涨跌: {_pct(ret_60d)}")

            industry_ret = getattr(row, "industry_ret_60d", None)
            if industry_ret is not None and not pd.isna(industry_ret):
                lines_local.append(f"- 行业近60日涨跌: {_pct(industry_ret)}")

            industry_alignment = getattr(row, "industry_alignment", None)
            if industry_alignment is not None and not pd.isna(industry_alignment):
                lines_local.append(f"- 行业上行对齐: {'是' if industry_alignment else '否'}")

            vol_horizons = getattr(row, "vol_horizons", "")
            if isinstance(vol_horizons, str) and vol_horizons:
                lines_local.append(f"- 波动收缩突破可用周期: {vol_horizons}天")

            for rule_key in ["trend_follow", "pullback_in_uptrend", "vol_contraction_breakout"]:
                signal_flag = getattr(row, f"{rule_key}_signal", False)
                if not signal_flag:
                    continue
                rule_name = rule_labels.get(rule_key, rule_key)
                date_val = getattr(row, f"{rule_key}_date", "")
                close_val = _num(getattr(row, f"{rule_key}_close", None), 2)
                returns_text = []
                for h in config.horizons:
                    ret_val = getattr(row, f"{rule_key}_ret_{h}", None)
                    if ret_val is None or pd.isna(ret_val):
                        continue
                    returns_text.append(f"{h}日 {_pct(ret_val)}")
                ret_str = "，".join(returns_text) if returns_text else "-"
                lines_local.append(
                    f"- {rule_name}信号: {date_val} | 触发价: {close_val} | 收益: {ret_str}"
                )

            lines_local.append("")
        return lines_local

    signal_mask = (
        df_detail.get("trend_follow_signal", False)
        | df_detail.get("pullback_in_uptrend_signal", False)
        | df_detail.get("vol_contraction_breakout_signal", False)
    )
    df_signal = df_detail[signal_mask].copy()
    selected_mask = signal_mask & df_detail.get("industry_alignment", False)
    df_selected = df_detail[selected_mask].copy()

    lines = []
    lines.append(f"# 多规则趋势分析报告 ({datetime.now().strftime('%Y%m%d_%H%M%S')})")
    lines.append("")
    lines.append(f"- 回看天数: {config.lookback_days}")
    lines.append(f"- 收益周期(天): {', '.join(map(str, config.horizons))}")
    lines.append("")
    lines.append("## 汇总统计（仅含有信号样本）")
    lines.append("")
    lines.append(_format_summary_table(df_summary))
    lines.append("")
    lines.append("## 有信号数量")
    lines.append("")
    lines.append(f"- 有信号股票数: {len(df_signal)}")
    lines.append(f"- 全部股票数: {len(df_detail)}")
    lines.append("")
    lines.append("## 选择规则建议（兼顾稳健与收益）")
    lines.append("")
    min_count = 100
    valid = df_summary.copy()
    valid = valid[(valid["count"] >= min_count) & valid["hit_rate"].notna() & valid["avg_return"].notna()]
    if valid.empty:
        lines.append("样本不足，无法筛选最佳组合")
    else:
        best_hit = valid.loc[valid["hit_rate"].idxmax()]
        best_ret = valid.loc[valid["avg_return"].idxmax()]
        lines.append("优先: 行业上行对齐 + 样本充足（>=100）")
        lines.append("")
        lines.append("- 最高胜率组合: "
                     f"{_rule_label(str(best_hit['rule']))} / {int(best_hit['horizon'])}天 | "
                     f"样本 {int(best_hit['count'])} | 胜率 {_pct(best_hit['hit_rate'])} | 平均收益 {_pct(best_hit['avg_return'])}")
        lines.append("- 最高平均收益组合: "
                     f"{_rule_label(str(best_ret['rule']))} / {int(best_ret['horizon'])}天 | "
                     f"样本 {int(best_ret['count'])} | 胜率 {_pct(best_ret['hit_rate'])} | 平均收益 {_pct(best_ret['avg_return'])}")
        lines.append("")
        lines.append(f"筛选规则: 样本数 >= {min_count}，以胜率或平均收益排序")
    lines.append("")
    lines.append("## 信号组合分布")
    lines.append("")
    if not df_signal.empty:
        combo_df = df_signal[[
            "trend_follow_signal",
            "pullback_in_uptrend_signal",
            "vol_contraction_breakout_signal",
        ]].copy()
        combo_df["组合"] = (
            combo_df["trend_follow_signal"].map(lambda x: "趋势跟随" if x else "")
            + combo_df["pullback_in_uptrend_signal"].map(lambda x: "上升回撤" if x else "")
            + combo_df["vol_contraction_breakout_signal"].map(lambda x: "波动收缩突破" if x else "")
        )
        combo_counts = combo_df["组合"].value_counts().reset_index()
        combo_counts.columns = ["组合", "数量"]
        combo_counts["占比"] = combo_counts["数量"] / combo_counts["数量"].sum()
        combo_counts["占比"] = combo_counts["占比"].map(_pct)
        lines.append(combo_counts.to_markdown(index=False))
    else:
        lines.append("无信号样本")
    lines.append("")
    lines.append("## 板块分布（波动收缩突破）")
    lines.append("")
    lines.append("## 玄学指标（近10天内出现6涨1跌）")
    lines.append("")
    lines.append("- 规则: 最近10个交易日内，存在连续7天中‘6天上涨、1天下跌’的组合")
    lines.append("- 特别优先: 最新一天为下跌，且最近7天刚好满足‘6涨1跌’（今天是跌）")
    if "mystic_6up1down_10d" in df_detail.columns:
        lines.append(f"- 在优选股票内命中数: {int(df_selected['mystic_6up1down_10d'].sum()) if not df_selected.empty else 0}")
        if "mystic_today_down_7d" in df_detail.columns and not df_selected.empty:
            lines.append(f"- 其中『今天为跌且7天刚好6涨1跌』: {int(df_selected['mystic_today_down_7d'].sum())}")
        lines.append(f"- 优选股票总数: {len(df_selected)}")
    lines.append("")
    lines.append("## 玄学筛选结果（优选股票内）")
    lines.append("")
    if "mystic_6up1down_10d" in df_detail.columns and not df_selected.empty:
        mystic_df = df_selected[df_selected["mystic_6up1down_10d"] == True].copy()
        if mystic_df.empty:
            lines.append("无命中样本")
        else:
            lines.append("### 行业占比（玄学筛选结果）")
            if "industry" in mystic_df.columns:
                industry_counts = mystic_df["industry"].value_counts().reset_index()
                industry_counts.columns = ["行业", "数量"]
                industry_counts["占比"] = industry_counts["数量"] / industry_counts["数量"].sum()
                industry_counts["占比"] = industry_counts["占比"].map(_pct)
                lines.append(industry_counts.to_markdown(index=False))
            else:
                lines.append("缺少行业字段")
            lines.append("")
            if "mystic_today_down_after_6up" in mystic_df.columns:
                mystic_df = mystic_df.sort_values(
                    by=["mystic_today_down_after_6up", "latest_date"],
                    ascending=[False, False],
                )
            cols = [
                "code",
                "name",
                "board",
                "industry",
                "latest_date",
                "latest_close",
                "status",
                "mystic_today_down_after_6up",
                "mystic_today_is_6th_up",
            ]
            # 过滤不存在的列
            cols = [c for c in cols if c in mystic_df.columns]
            show_df = mystic_df[cols].rename(columns={
                "code": "代码",
                "name": "名称",
                "board": "板块",
                "industry": "行业",
                "latest_date": "最新日期",
                "latest_close": "最新价",
                "status": "状态",
                "mystic_today_down_after_6up": "[STAR]买入",
                "mystic_today_is_6th_up": "[STAR]等待",
            })
            for col in ["[STAR]买入", "[STAR]等待"]:
                if col in show_df.columns:
                    show_df[col] = show_df[col].map(lambda x: "是" if x else "")
            lines.append(show_df.to_markdown(index=False))
    else:
        lines.append("无命中样本")
    lines.append("")
    if "board" in df_detail.columns:
        board_df = df_signal[df_signal["vol_contraction_breakout_signal"] == True]
        if not board_df.empty:
            lines.append(_format_board_table(board_df))
        else:
            lines.append("无信号样本")
    else:
        lines.append("缺少板块字段")
    lines.append("")
    lines.append("## 行业趋势对比（波动收缩突破）")
    lines.append("")
    if "industry" in df_detail.columns and "industry_ret_60d" in df_detail.columns:
        industry_df = df_signal[df_signal["vol_contraction_breakout_signal"] == True].copy()
        if not industry_df.empty:
            industry_df["industry_up"] = industry_df["industry_ret_60d"] > 0
            industry_df["stock_up"] = industry_df["ret_60d"] > 0
            lines.append(_format_industry_compare(industry_df))
        else:
            lines.append("无信号样本")
    else:
        lines.append("缺少行业字段")
    lines.append("")
    lines.append("## 行业上行对齐汇总（追加）")
    lines.append("")
    aligned_rows = df_summary[df_summary["rule"].str.contains("_industry_up", na=False)]
    if not aligned_rows.empty:
        lines.append(_format_summary_table(aligned_rows))
    else:
        lines.append("无对齐样本")
    lines.append("")
    lines.append("## 期限覆盖统计（波动收缩突破）")
    lines.append("")
    if "vol_contraction_breakout_signal" in df_detail.columns:
        vdf = df_signal[df_signal["vol_contraction_breakout_signal"] == True].copy()
        if not vdf.empty:
            lines.append(_format_coverage_table(vdf))
        else:
            lines.append("无信号样本")
    else:
        lines.append("缺少信号字段")
    lines.append("")
    lines.append("## 股票明细（仅含有信号，按股票分块）")
    lines.append("")
    if df_signal.empty:
        lines.append("无信号样本")
    else:
        lines.extend(_format_detail_section(df_signal, limit=200))
        lines.append("(仅展示前200条，完整结果请查看明细CSV)")
    return "\n".join(lines)


def build_xuanxue_report(
    df_detail: pd.DataFrame,
    df_summary: pd.DataFrame,
    config: TrendRulesConfig,
    title: str,
    mode: str,
    strategy_name: str,
) -> str:
    def _pct(val: float | None) -> str:
        if val is None or pd.isna(val):
            return "-"
        return f"{val:.2%}"

    def _num(val: float | None, digits: int = 2) -> str:
        if val is None or pd.isna(val):
            return "-"
        return f"{val:.{digits}f}"

    def _format_summary_table(summary_df: pd.DataFrame) -> str:
        df = summary_df.copy()
        df = df.rename(columns={
            "rule": "策略",
            "horizon": "周期(天)",
            "count": "样本数",
            "hit_rate": "胜率",
            "avg_return": "平均收益",
        })
        if "胜率" in df.columns:
            df["胜率"] = df["胜率"].map(_pct)
        if "平均收益" in df.columns:
            df["平均收益"] = df["平均收益"].map(_pct)
        return df.to_markdown(index=False)

    # 构建信号掩码
    signal_cols = ["trend_follow_signal", "pullback_in_uptrend_signal", "vol_contraction_breakout_signal"]
    signal_mask = pd.Series(False, index=df_detail.index)
    for col in signal_cols:
        if col in df_detail.columns:
            signal_mask = signal_mask | df_detail[col].fillna(False).astype(bool)
    df_signal = df_detail[signal_mask].copy()

    # 构建玄学掩码
    if mode == "6up1down":
        mystic_col = "mystic_6up1down_10d"
    else:
        mystic_col = "mystic_consecutive_6up"
    
    if mystic_col in df_signal.columns:
        mystic_mask = df_signal[mystic_col].fillna(False).astype(bool)
    else:
        mystic_mask = pd.Series(False, index=df_signal.index)

    mystic_df = df_signal[mystic_mask].copy()

    lines = []
    lines.append(f"# {title} ({datetime.now().strftime('%Y%m%d_%H%M%S')})")
    lines.append("")
    lines.append(f"- 策略: {strategy_name}")
    lines.append("- 组合条件: 3(多规则趋势分析)")
    lines.append("- 说明: 不包含 1(稳步上升) 和 4(网格测试)")
    lines.append("")
    lines.append(f"- 回看天数: {config.lookback_days}")
    lines.append(f"- 收益周期(天): {', '.join(map(str, config.horizons))}")
    lines.append("")
    lines.append("## 汇总统计（仅含有信号样本）")
    lines.append("")
    lines.append(_format_summary_table(df_summary))
    lines.append("")
    lines.append("## 有信号数量")
    lines.append("")
    lines.append(f"- 有信号股票数: {len(df_signal)}")
    lines.append(f"- 全部股票数: {len(df_detail)}")

    if not df_signal.empty and "industry_up" in df_signal.columns and "stock_up" in df_signal.columns:
        align_count = int(df_signal.get("industry_alignment", False).sum())
        industry_up_count = int(df_signal.get("industry_up", False).sum())
        stock_up_count = int(df_signal.get("stock_up", False).sum())
        lines.append(f"- 行业上行对齐: {align_count} / {len(df_signal)} ({_pct(align_count / len(df_signal))})")
        lines.append(f"- 行业上行: {industry_up_count} / {len(df_signal)} ({_pct(industry_up_count / len(df_signal))})")
        lines.append(f"- 个股上行: {stock_up_count} / {len(df_signal)} ({_pct(stock_up_count / len(df_signal))})")

    lines.append("")
    if mode == "6up1down":
        lines.append("## 玄学条件1（近10天内出现6涨1跌）")
        lines.append("")
        lines.append("- 规则: 最近10个交易日内，存在连续7天中‘6天上涨、1天下跌’的组合")
        lines.append("- 特别优先: 最新一天为下跌，且最近7天刚好满足‘6涨1跌’（今天是跌）")
    else:
        lines.append("## 玄学条件2（连续6天阳线）")
        lines.append("")
        lines.append("- 规则: 最近6个交易日连续阳线")
        lines.append("- 排序优先: 连续6天阳线的前一天为阴线优先，其次为前一天为阳线")

    lines.append("")
    lines.append("## 玄学筛选结果（仅含有信号样本）")
    lines.append("")
    if mystic_df.empty:
        lines.append("无命中样本")
        return "\n".join(lines)

    lines.append("### 板块统计（玄学结果）")
    if "board" in mystic_df.columns:
        board_counts = mystic_df["board"].fillna("未知板块").value_counts().reset_index()
        board_counts.columns = ["板块", "数量"]
        board_counts["占比"] = board_counts["数量"] / board_counts["数量"].sum()
        board_counts["占比"] = board_counts["占比"].map(_pct)
        lines.append(board_counts.to_markdown(index=False))
    else:
        lines.append("缺少板块字段")
    lines.append("")
    lines.append("### 行业统计（玄学结果）")
    if "industry" in mystic_df.columns:
        industry_counts = mystic_df["industry"].fillna("未知行业").value_counts().reset_index()
        industry_counts.columns = ["行业", "数量"]
        industry_counts["占比"] = industry_counts["数量"] / industry_counts["数量"].sum()
        industry_counts["占比"] = industry_counts["占比"].map(_pct)
        lines.append(industry_counts.to_markdown(index=False))
    else:
        lines.append("缺少行业字段")
    lines.append("")

    if mode == "6up1down" and "mystic_today_down_after_6up" in mystic_df.columns:
        mystic_df = mystic_df.sort_values(
            by=["mystic_today_down_after_6up", "latest_date"],
            ascending=[False, False],
        )
    if mode == "6up" and "mystic_6up_prev_down" in mystic_df.columns:
        mystic_df = mystic_df.sort_values(
            by=["mystic_6up_prev_down", "latest_date"],
            ascending=[False, False],
        )

    cols = [
        "code",
        "name",
        "board",
        "industry",
        "latest_date",
        "latest_close",
        "status",
        "industry_up",
        "stock_up",
        "industry_alignment",
    ]
    if mode == "6up1down":
        cols.append("mystic_today_down_after_6up")
        cols.append("mystic_today_is_6th_up")
    else:
        cols.append("mystic_6up_prev_down")
    
    # 过滤不存在的列
    cols = [c for c in cols if c in mystic_df.columns]

    show_df = mystic_df[cols].rename(columns={
        "code": "代码",
        "name": "名称",
        "board": "板块",
        "industry": "行业",
        "latest_date": "最新日期",
        "latest_close": "最新价",
        "status": "状态",
        "industry_up": "行业上行",
        "stock_up": "个股上行",
        "industry_alignment": "行业上行对齐",
        "mystic_today_down_after_6up": "[STAR]买入",
        "mystic_today_is_6th_up": "[STAR]等待",
        "mystic_6up_prev_down": "6连阳前一天为阴线",
    })
    for col in ["行业上行", "个股上行", "行业上行对齐", "[STAR]买入", "[STAR]等待", "6连阳前一天为阴线"]:
        if col in show_df.columns:
            show_df[col] = show_df[col].map(lambda x: "是" if x else "")
    show_df["最新价"] = show_df["最新价"].map(lambda x: _num(x, 2))
    lines.append(show_df.to_markdown(index=False))
    return "\n".join(lines)


def count_xuanxue_candidates(df_detail: pd.DataFrame, mode: str) -> int:
    """统计满足玄学条件的候选数量"""
    # 先筛选有趋势信号的股票
    signal_cols = ["trend_follow_signal", "pullback_in_uptrend_signal", "vol_contraction_breakout_signal"]
    signal_mask = pd.Series(False, index=df_detail.index)
    for col in signal_cols:
        if col in df_detail.columns:
            signal_mask = signal_mask | df_detail[col].fillna(False).astype(bool)
    
    df_signal = df_detail[signal_mask].copy()
    if df_signal.empty:
        return 0
    
    # 根据模式选择玄学条件列
    if mode == "6up1down":
        mystic_col = "mystic_6up1down_10d"
    else:
        mystic_col = "mystic_consecutive_6up"
    
    if mystic_col not in df_signal.columns:
        return 0
    
    mystic_mask = df_signal[mystic_col].fillna(False).astype(bool)
    return int(mystic_mask.sum())


def main() -> int:
    parser = argparse.ArgumentParser(description="多规则趋势分析（本地数据）")
    parser.add_argument("--limit", type=int, default=None, help="限制分析数量")
    parser.add_argument("--lookback", type=int, default=120, help="信号回看天数")
    parser.add_argument("--horizons", type=str, default="5,20,60", help="收益区间，如 5,20,60")
    args = parser.parse_args()

    horizons = [int(h.strip()) for h in args.horizons.split(",") if h.strip()]
    config = TrendRulesConfig(lookback_days=args.lookback, horizons=horizons)

    records = []
    industry_map = load_industry_map()
    total = len(load_selected_stocks()) if args.limit is None else args.limit
    items = iter_stock_items(limit=args.limit)
    if _HAS_TQDM:
        items = tqdm(list(items), total=total, desc="分析进度")
    else:
        items = list(items)

    for idx, item in enumerate(items, 1):
        df = load_daily_data(item.code)
        if df.empty or len(df) < config.min_bars:
            records.append({
                "code": item.code,
                "name": item.name,
                "status": "数据不足",
            })
        else:
            result = analyze_stock(df, config.lookback_days, config.horizons)
            result.update({
                "code": item.code,
                "name": item.name,
                "board": get_board_type(item.code),
                "industry": industry_map.get(item.code, ""),
            })
            records.append(result)

        if not _HAS_TQDM and (idx % 200 == 0 or idx == total):
            print(f"分析进度: {idx}/{total}")

    df_detail = pd.DataFrame(records)
    if "industry" in df_detail.columns and "ret_60d" in df_detail.columns:
        industry_mean = (
            df_detail[df_detail["ret_60d"].notna()]
            .groupby("industry")["ret_60d"]
            .mean()
            .to_dict()
        )
        df_detail["industry_ret_60d"] = df_detail["industry"].map(industry_mean)
        df_detail["industry_up"] = df_detail["industry_ret_60d"] > 0
        df_detail["stock_up"] = df_detail["ret_60d"] > 0
        df_detail["industry_alignment"] = df_detail["industry_up"] & df_detail["stock_up"]
    if "vol_contraction_breakout_ret_5" in df_detail.columns:
        def _horizon_label(row) -> str:
            horizons = []
            for h in config.horizons:
                col = f"vol_contraction_breakout_ret_{h}"
                if col in row and pd.notna(row[col]):
                    horizons.append(str(h))
            return ",".join(horizons)

        df_detail["vol_horizons"] = df_detail.apply(_horizon_label, axis=1)

    df_summary = summarize_results(df_detail, config.horizons)
    if "industry_alignment" in df_detail.columns:
        aligned = df_detail[df_detail["industry_alignment"] == True].copy()
        if not aligned.empty:
            aligned_summary = summarize_results(aligned, config.horizons)
            aligned_summary["rule"] = aligned_summary["rule"].map(lambda r: f"{r}_industry_up")
            df_summary = pd.concat([df_summary, aligned_summary], ignore_index=True)

    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    batch_date = now.strftime("%Y-%m-%d")
    batch_time = now.strftime("%H-%M-%S")
    batch_dir = output_dir / batch_date / batch_time
    batch_dir.mkdir(parents=True, exist_ok=True)

    detail_path = batch_dir / f"trend_rules_detail_{ts}.csv"
    summary_path = batch_dir / f"trend_rules_summary_{ts}.csv"
    report_path = batch_dir / f"trend_rules_report_{ts}.md"
    stats_path = batch_dir / f"trend_rules_stats_{ts}.md"
    xuanxue61_count = count_xuanxue_candidates(df_detail, "6up1down")
    xuanxue6_count = count_xuanxue_candidates(df_detail, "6up")
    base_label = "baseon_unknown"
    if "latest_date" in df_detail.columns:
        base_date = pd.to_datetime(df_detail["latest_date"], errors="coerce").max()
        if pd.notna(base_date):
            base_label = f"baseon_{base_date.strftime('%m%d%Y')}"
    xuanxue61_path = batch_dir / f"xuanxue_3_61_{xuanxue61_count}只_{base_label}_{ts}.md"
    xuanxue6_path = batch_dir / f"xuanxue_3_6_{xuanxue6_count}只_{base_label}_{ts}.md"

    # 列名映射（英文 -> 中文）
    detail_columns_cn = {
        "latest_date": "最新日期",
        "latest_close": "最新价",
        "status": "状态",
        "ret_60d": "近60日涨跌",
        # 玄学指标（新字段名）
        "mystic_6up1down_10d": "玄学_10天内有6连阳后1阴",
        "mystic_consecutive_6up": "玄学_最近6天连续阳线",
        "mystic_today_down_after_6up": "玄学_今天阴线且前6天连阳(回调)",
        "mystic_today_is_6th_up": "玄学_今天是第6天阳线(追涨)",
        "mystic_6up_prev_down": "玄学_6连阳前一天是阴线",
        # 趋势规则
        "trend_follow_signal": "趋势跟随_是否信号",
        "pullback_in_uptrend_signal": "上升回撤_是否信号",
        "vol_contraction_breakout_signal": "波动收缩突破_是否信号",
        "code": "代码",
        "name": "名称",
        "board": "板块",
        "industry": "行业",
        "trend_follow_date": "趋势跟随_信号日期",
        "trend_follow_close": "趋势跟随_触发价",
        "trend_follow_ret_5": "趋势跟随_5日收益",
        "trend_follow_ret_20": "趋势跟随_20日收益",
        "trend_follow_ret_60": "趋势跟随_60日收益",
        "pullback_in_uptrend_date": "上升回撤_信号日期",
        "pullback_in_uptrend_close": "上升回撤_触发价",
        "pullback_in_uptrend_ret_5": "上升回撤_5日收益",
        "pullback_in_uptrend_ret_20": "上升回撤_20日收益",
        "pullback_in_uptrend_ret_60": "上升回撤_60日收益",
        "vol_contraction_breakout_date": "波动收缩突破_信号日期",
        "vol_contraction_breakout_close": "波动收缩突破_触发价",
        "vol_contraction_breakout_ret_5": "波动收缩突破_5日收益",
        "vol_contraction_breakout_ret_20": "波动收缩突破_20日收益",
        "vol_contraction_breakout_ret_60": "波动收缩突破_60日收益",
        "industry_ret_60d": "行业近60日涨跌",
        "industry_up": "行业上行",
        "stock_up": "个股上行",
        "industry_alignment": "行业上行对齐",
        "vol_horizons": "波动收缩突破_可用周期",
    }
    summary_columns_cn = {
        "rule": "策略",
        "horizon": "周期(天)",
        "count": "样本数",
        "hit_rate": "胜率",
        "avg_return": "平均收益",
    }

    df_detail_cn = df_detail.rename(columns=detail_columns_cn)
    df_summary_cn = df_summary.rename(columns=summary_columns_cn)

    df_detail_cn.to_csv(detail_path, index=False, encoding="utf-8-sig")
    df_summary_cn.to_csv(summary_path, index=False, encoding="utf-8-sig")

    mystic_path = output_dir / f"mystic_candidates_{ts}.csv"
    if "mystic_6up1down_10d" in df_detail.columns:
        signal_mask = (
            df_detail.get("trend_follow_signal", False)
            | df_detail.get("pullback_in_uptrend_signal", False)
            | df_detail.get("vol_contraction_breakout_signal", False)
        )
        selected_mask = signal_mask & df_detail.get("industry_alignment", False)
        mystic_df = df_detail[selected_mask & (df_detail["mystic_6up1down_10d"] == True)].copy()
        if not mystic_df.empty:
            mystic_df = mystic_df.rename(columns=detail_columns_cn)
        mystic_df.to_csv(mystic_path, index=False, encoding="utf-8-sig")

    report_text = build_report(df_detail, df_summary, config)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    xuanxue61_text = build_xuanxue_report(
        df_detail,
        df_summary,
        config,
        title="玄学条件1报告（6涨1跌）",
        mode="6up1down",
        strategy_name="xuanxue_3_61",
    )
    with open(xuanxue61_path, "w", encoding="utf-8") as f:
        f.write(xuanxue61_text)

    xuanxue6_text = build_xuanxue_report(
        df_detail,
        df_summary,
        config,
        title="玄学条件2报告（连续6天阳线）",
        mode="6up",
        strategy_name="xuanxue_3_6",
    )
    with open(xuanxue6_path, "w", encoding="utf-8") as f:
        f.write(xuanxue6_text)

    stats_lines = []
    stats_lines.append(f"# 趋势规则统计摘要 ({ts})")
    stats_lines.append("")
    stats_lines.append(f"- 回看天数: {config.lookback_days}")
    stats_lines.append(f"- 收益区间: {', '.join(map(str, config.horizons))}")
    stats_lines.append("")

    stats_lines.append("## 信号数量")
    stats_lines.append("")
    if "vol_contraction_breakout_signal" in df_detail.columns:
        total_signal = int(df_detail["vol_contraction_breakout_signal"].sum())
        aligned_signal = int(df_detail.get("industry_alignment", False).sum()) if "industry_alignment" in df_detail.columns else 0
        stats_lines.append(f"- 波动收缩突破: {total_signal}")
        stats_lines.append(f"- 波动收缩突破 + 行业上行对齐: {aligned_signal}")
    stats_lines.append("")

    stats_lines.append("## 期限覆盖统计（波动收缩突破）")
    stats_lines.append("")
    if "vol_contraction_breakout_signal" in df_detail.columns:
        vdf = df_detail[df_detail["vol_contraction_breakout_signal"] == True].copy()
        coverage = []
        for h in config.horizons:
            col = f"vol_contraction_breakout_ret_{h}"
            if col in vdf.columns:
                coverage.append({
                    "周期(天)": h,
                    "样本数": int(vdf[col].notna().sum()),
                    "占比": float(vdf[col].notna().mean()) if len(vdf) else 0,
                })
        stats_df = pd.DataFrame(coverage)
        if not stats_df.empty:
            stats_df["占比"] = stats_df["占比"].map(lambda x: f"{x:.2%}" if x is not None else "-")
        stats_lines.append(stats_df.to_markdown(index=False))

    with open(stats_path, "w", encoding="utf-8") as f:
        f.write("\n".join(stats_lines))

    print(f"[OK] 明细输出：{detail_path}")
    print(f"[OK] 汇总输出：{summary_path}")
    print(f"[OK] 报告输出：{report_path}")
    print(f"[OK] 玄学报告1：{xuanxue61_path}")
    print(f"[OK] 玄学报告2：{xuanxue6_path}")
    print(f"[OK] 统计摘要：{stats_path}")
    print(f"[OK] 玄学筛选：{mystic_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
