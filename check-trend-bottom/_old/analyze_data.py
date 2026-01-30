# -*- coding: utf-8 -*-
"""
分析A股日K/周K/月K统计摘要 + TD九底分析

输入：
- data/selected_stocks.csv
- data/raw/{code}.csv

输出：
- output/analysis_summary_YYYYMMDD_HHMMSS.csv
"""
import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import pandas as pd
import baostock as bs

DEFAULT_DAYS = 365


def get_board_type(code: str) -> str:
    """根据股票代码判断所属交易板块"""
    if code.startswith('688'):
        return '科创板'
    elif code.startswith('300') or code.startswith('301'):
        return '创业板'
    elif code.startswith('8'):
        return '北交所'
    elif code.startswith('002') or code.startswith('000'):
        return '深圳主板'
    elif code.startswith('60'):
        return '上海主板'
    else:
        return '其他'


def get_stock_industry(bs_code: str) -> str:
    """获取股票所属行业（证监会分类）"""
    try:
        rs = bs.query_stock_industry(code=bs_code)
        if rs.error_code == '0' and rs.next():
            data = rs.get_row_data()
            if len(data) > 3 and data[3]:
                # 去掉行业代码前缀，如"J66货币金融服务" -> "货币金融服务"
                return re.sub(r'^[A-Z]\d+', '', data[3]) or data[3]
        return '未知'
    except Exception:
        return '未知'


def load_selected_stocks(selected_path: Path) -> pd.DataFrame:
    if not selected_path.exists():
        raise FileNotFoundError("找不到 selected_stocks.csv，请先运行 fetch_data.py")
    return pd.read_csv(selected_path)


def load_daily_data(raw_dir: Path, code: str) -> pd.DataFrame:
    path = raw_dir / f"{code}.csv"
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        df = pd.read_csv(path)
    
    if df.empty:
        return pd.DataFrame()
    
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    if not all(col in df.columns for col in ["date", "open", "high", "low", "close", "volume"]):
        return pd.DataFrame()
    
    selected_df = df[["date", "open", "high", "low", "close", "volume"]].copy()
    selected_df["date"] = pd.to_datetime(selected_df["date"], errors="coerce")
    selected_df = selected_df.dropna(subset=["date"])
    selected_df = selected_df.sort_values(by="date")
    return selected_df


def filter_recent_days(df: pd.DataFrame, days: int) -> pd.DataFrame:
    if df.empty:
        return df
    last_date = df["date"].max()
    cutoff = last_date - timedelta(days=days)
    return df[df["date"] >= cutoff].copy()


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    df_copy = df.set_index("date")
    resampled = df_copy.resample(rule).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    )
    resampled = resampled.dropna().reset_index()
    return resampled


def summarize_period(df: pd.DataFrame, prefix: str) -> Dict[str, object]:
    if df.empty:
        return {
            f"{prefix}_last_date": "",
            f"{prefix}_last_close": None,
            f"{prefix}_high_365": None,
            f"{prefix}_low_365": None,
            f"{prefix}_mean_365": None,
            f"{prefix}_rows": 0,
        }

    last_row = df.iloc[-1]
    return {
        f"{prefix}_last_date": pd.Timestamp(last_row["date"]).strftime("%Y-%m-%d"),
        f"{prefix}_last_close": float(last_row["close"]),
        f"{prefix}_high_365": float(df["high"].max()),
        f"{prefix}_low_365": float(df["low"].min()),
        f"{prefix}_mean_365": float(df["close"].mean()),
        f"{prefix}_rows": int(len(df)),
    }


def calculate_td_sequence(close_prices: pd.Series) -> List[int]:
    sequence: List[int] = []
    current = 0
    for idx in range(len(close_prices)):
        if idx < 4:
            sequence.append(0)
            continue
        if close_prices.iloc[idx] < close_prices.iloc[idx - 4]:
            current = current + 1 if current < 9 else 1
        else:
            current = 0
        sequence.append(current)
    return sequence


def get_td_info(df: pd.DataFrame, prefix: str) -> Dict[str, object]:
    if df.empty or "close" not in df.columns:
        return {
            f"{prefix}_td_count": 0,
            f"{prefix}_is_jiudi": False,
            f"{prefix}_is_near_jiudi": False,
            f"{prefix}_last_jiudi_date": "",
            f"{prefix}_last_jiudi_price": None,
        }

    close_series = df["close"].reset_index(drop=True)
    sequence = calculate_td_sequence(close_series)
    td_count = int(sequence[-1]) if sequence else 0

    last_jiudi_date = ""
    last_jiudi_price = None
    for idx in range(len(sequence) - 1, -1, -1):
        if sequence[idx] >= 9:
            row = df.iloc[idx]
            last_jiudi_date = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
            last_jiudi_price = float(row["close"])
            break

    return {
        f"{prefix}_td_count": td_count,
        f"{prefix}_is_jiudi": td_count >= 9,
        f"{prefix}_is_near_jiudi": td_count >= 7,
        f"{prefix}_last_jiudi_date": last_jiudi_date,
        f"{prefix}_last_jiudi_price": last_jiudi_price,
    }


def build_resonance(daily_td: int, weekly_td: int, monthly_td: int) -> Dict[str, object]:
    cycles = sum(count >= 9 for count in [daily_td, weekly_td, monthly_td])
    if cycles == 3:
        level = "三周期九底"
    elif cycles == 2:
        level = "双周期九底"
    elif cycles == 1:
        level = "单周期九底"
    else:
        level = "无九底"
    return {"jiudi_cycles": cycles, "resonance_level": level}


def analyze_stock(df_daily: pd.DataFrame) -> Dict[str, object]:
    df_daily = df_daily.copy()
    
    try:
        df_daily = df_daily[["date", "open", "high", "low", "close", "volume"]]
    except KeyError as e:
        missing = set(["date", "open", "high", "low", "close", "volume"]) - set(df_daily.columns)
        return {"error": str(e), "available_cols": list(df_daily.columns)}
    
    df_weekly = resample_ohlcv(df_daily, "W")
    df_monthly = resample_ohlcv(df_daily, "ME")

    summary = {}
    summary.update(summarize_period(df_daily, "daily"))
    summary.update(summarize_period(df_weekly, "weekly"))
    summary.update(summarize_period(df_monthly, "monthly"))

    summary.update(get_td_info(df_daily, "daily"))
    summary.update(get_td_info(df_weekly, "weekly"))
    summary.update(get_td_info(df_monthly, "monthly"))

    resonance = build_resonance(
        summary["daily_td_count"],
        summary["weekly_td_count"],
        summary["monthly_td_count"],
    )
    summary.update(resonance)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="A股日K/周K/月K统计摘要 + 九底分析")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="最近天数（默认365）")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"
    raw_dir = data_dir / "raw"
    output_dir = base_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_path = data_dir / "selected_stocks.csv"
    output_path = output_dir / f"analysis_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    # 登录BaoStock获取行业信息
    print("[*] 连接 BaoStock...")
    lg = bs.login()
    if lg.error_code != '0':
        print(f"[!] BaoStock登录失败: {lg.error_msg}，行业信息将显示为'未知'")
    
    selected_df = load_selected_stocks(selected_path)
    results: List[Dict[str, object]] = []
    missing_cols_count = 0
    other_error_count = 0
    total = len(selected_df)
    print(f"[*] 开始分析 {total} 只股票...")

    for idx, row in enumerate(selected_df.itertuples(index=False), 1):
        code = str(getattr(row, "code"))
        name = str(getattr(row, "name", ""))
        bs_code = str(getattr(row, "bs_code", ""))
        
        # 如果没有bs_code，根据代码推断
        if not bs_code:
            bs_code = f"sh.{code}" if code.startswith('6') else f"sz.{code}"
        
        try:
            df_daily = load_daily_data(raw_dir, code)
            df_daily = filter_recent_days(df_daily, args.days)

            analysis = analyze_stock(df_daily)
            if "error" in analysis:
                missing_cols_count += 1
                if missing_cols_count <= 5:
                    print(f"[!] {code} {name} 数据列不足，跳过")
                continue
            analysis.update({
                "code": code, 
                "name": name,
                "board": get_board_type(code),
                "industry": get_stock_industry(bs_code),
            })
            results.append(analysis)
            if idx % 100 == 0 or idx == total:
                print(
                    f"[*] 进度: {idx}/{total} ({idx/total*100:.1f}%) | "
                    f"成功: {len(results)} | 无效: {missing_cols_count} | 其他错误: {other_error_count}"
                )
        except Exception as e:
            other_error_count += 1
            print(f"[!] {code} {name} 分析失败: {str(e)}")
            continue

    # 登出BaoStock
    bs.logout()
    print("[*] 已断开 BaoStock 连接")

    result_df = pd.DataFrame(results)

    # 字段顺序：股票标识 > 板块分类 > 核心筛选指标 > 九底状态 > 最近九底位置 > 最新行情 > 价格区间 > 周期统计 > 辅助字段
    column_order = [
        # 1. 股票标识
        "code", "name",
        # 2. 板块分类
        "board", "industry",
        # 3. 核心筛选指标
        "daily_td_count", "weekly_td_count", "monthly_td_count", "jiudi_cycles", "resonance_level",
        # 4. 九底状态标记
        "daily_is_jiudi", "daily_is_near_jiudi",
        "weekly_is_jiudi", "weekly_is_near_jiudi",
        "monthly_is_jiudi", "monthly_is_near_jiudi",
        # 5. 最近九底位置
        "daily_last_jiudi_date", "daily_last_jiudi_price",
        "weekly_last_jiudi_date", "weekly_last_jiudi_price",
        "monthly_last_jiudi_date", "monthly_last_jiudi_price",
        # 6. 最新行情
        "daily_last_date", "daily_last_close",
        "weekly_last_date", "weekly_last_close",
        "monthly_last_date", "monthly_last_close",
        # 7. 价格区间
        "daily_high_365", "daily_low_365", "daily_mean_365",
        "weekly_high_365", "weekly_low_365", "weekly_mean_365",
        "monthly_high_365", "monthly_low_365", "monthly_mean_365",
        # 8. 周期统计（放最后）
        "daily_rows", "weekly_rows", "monthly_rows",
        # 9. 辅助字段（仅在出错时出现）
        "available_cols", "error",
    ]
    result_df = result_df[[col for col in column_order if col in result_df.columns]]

    # 字段中文名称映射
    column_names_cn = {
        # 1. 股票标识
        "code": "股票代码",
        "name": "股票名称",
        # 2. 板块分类
        "board": "交易板块",
        "industry": "行业",
        # 3. 核心筛选指标
        "daily_td_count": "日九底计数",
        "weekly_td_count": "周九底计数",
        "monthly_td_count": "月九底计数",
        "jiudi_cycles": "九底周期数",
        "resonance_level": "共振级别",
        # 3. 九底状态标记
        "daily_is_jiudi": "日九底",
        "daily_is_near_jiudi": "日接近九底",
        "weekly_is_jiudi": "周九底",
        "weekly_is_near_jiudi": "周接近九底",
        "monthly_is_jiudi": "月九底",
        "monthly_is_near_jiudi": "月接近九底",
        # 4. 最近九底位置
        "daily_last_jiudi_date": "日最近九底日期",
        "daily_last_jiudi_price": "日最近九底价格",
        "weekly_last_jiudi_date": "周最近九底日期",
        "weekly_last_jiudi_price": "周最近九底价格",
        "monthly_last_jiudi_date": "月最近九底日期",
        "monthly_last_jiudi_price": "月最近九底价格",
        # 5. 最新行情
        "daily_last_date": "日最新日期",
        "daily_last_close": "日最新收盘价",
        "weekly_last_date": "周最新日期",
        "weekly_last_close": "周最新收盘价",
        "monthly_last_date": "月最新日期",
        "monthly_last_close": "月最新收盘价",
        # 6. 价格区间
        "daily_high_365": "日最高价(365天)",
        "daily_low_365": "日最低价(365天)",
        "daily_mean_365": "日均价(365天)",
        "weekly_high_365": "周最高价(365天)",
        "weekly_low_365": "周最低价(365天)",
        "weekly_mean_365": "周均价(365天)",
        "monthly_high_365": "月最高价(365天)",
        "monthly_low_365": "月最低价(365天)",
        "monthly_mean_365": "月均价(365天)",
        # 7. 周期统计
        "daily_rows": "日K数量",
        "weekly_rows": "周K数量",
        "monthly_rows": "月K数量",
        # 8. 辅助字段
        "available_cols": "可用列",
        "error": "错误信息",
    }
    
    # 重命名字段为中文
    result_df = result_df.rename(columns=column_names_cn)

    # 将布尔值的 True/False 改为勾/×
    bool_columns = ["日九底", "日接近九底", "周九底", "周接近九底", "月九底", "月接近九底"]
    for col in bool_columns:
        if col in result_df.columns:
            result_df[col] = result_df[col].map(lambda x: "勾" if x is True or x == True else ("×" if x is False or x == False else x))

    result_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[OK] 分析完成：{output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
