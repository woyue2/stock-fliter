"""
[INPUT]:    依赖 get-data/data/stocks.db 提供的 K 线数据
[OUTPUT]:   生成包含每日胜率统计的 CSV 文件
[POS]:      回测验证模块，用于评估 Smile Number 策略的历史表现
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

try:
    from tqdm import tqdm
except Exception:
    tqdm = None

# --- Configuration ---
DB_PATH = "get-data/data/stocks.db"
TARGET_DATE = "2026-03-04"
BUY_DATE = "2026-03-05"
EXIT_DATES = ["2026-03-06", "2026-03-09"]

def check_magic(price):
    if price <= 0: return False
    pl = round(price, 2)
    # 提取各数字位 (对齐通达信 D0-D4)
    d0 = int(pl // 100) % 10  # 百位
    d1 = int(pl // 10) % 10   # 十位
    d2 = int(pl // 1) % 10    # 个位
    d3 = int(pl * 10) % 10    # 十分位
    d4 = int(pl * 100) % 10   # 百分位
    
    # 1. 四位基础形态 (PL >= 10)
    base_4bit = False
    if pl >= 10:
        base_4bit = (
            (d1 == d2 == d3 == d4) or                   # AAAA
            (d1 == d2 and d3 == d4) or                  # AABB
            (d1 == d3 and d2 == d4) or                  # ABAB
            (d1 == d4 and d2 == d3) or                  # ABBA
            (d1 == d3 and abs(d2 - d4) == 1)            # ABAC
        )

    # 2. 三位基础形态 (AAA, ABA, CC, 尾0, 顺子)
    base_3bit = (
        (d2 == d3 == d4) or                             # AAA
        (d2 == d4) or                                   # ABA
        (d3 == d4) or                                   # CC
        (d4 == 0) or                                    # 尾数0
        (d2 == d3 - 1 == d4 - 2) or                     # 顺子 123
        (d2 == d3 + 1 == d4 + 2)                        # 逆顺 321
    )
    
    # 3. 数学运算 (按价格区间严格隔离，防止 13.07 之类的跳位误判)
    # A. 一位数带两位小数运算 (仅限 PL < 10)
    math_1bit = False
    if pl < 10:
        math_1bit = (
            (d2 + d3 == d4 or d2 + d4 == d3 or d3 + d4 == d2) or
            ((d2 * d3 == d4 or d2 * d4 == d3 or d3 * d4 == d2) and pl >= 1) or
            ((d2 + d3 + d4) % 10 == 0 and (d2 + d3 + d4) > 0)
        )
    
    # B. 两位数带两位小数运算 (10 <= PL < 100)
    math_2bit = False
    if 10 <= pl < 100:
        math_2bit = (
            ((d1 + d2 + d3 + d4) % 10 == 0 and (d1 + d2 + d3 + d4) > 0) or  # 全位合十
            (d1 + d2 == d3 + d4) or (d1 + d4 == d2 + d3) or (d1 + d3 == d2 + d4) or
            (d1 + d2 + d3 == d4 or d1 + d2 + d4 == d3 or d1 + d3 + d4 == d2 or d2 + d3 + d4 == d1) or
            (d1 * d2 == d3 * d4 and pl >= 1)
        )
        
    math_3bit = False
    if pl >= 100:
        math_3bit = ((d0 + d1 + d2 + d3 + d4) % 10 == 0 and (d0 + d1 + d2 + d3 + d4) > 0)

    # 4. 整数平衡 (如 13.94 -> 13 = 9+4)
    int_math = (int(pl) == d3 + d4) or (int(pl) == d3 * d4)
    
    return base_4bit or base_3bit or math_1bit or math_2bit or math_3bit or int_math

def _pick_kline_table(conn: sqlite3.Connection) -> str:
    df = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)
    names = set(df["name"].tolist()) if not df.empty else set()
    if "daily_kline" in names:
        return "daily_kline"
    if "daily_ohlcv" in names:
        return "daily_ohlcv"
    raise RuntimeError(f"no kline table found")

def _get_trading_calendar(conn: sqlite3.Connection, table: str) -> list[str]:
    df = pd.read_sql_query(f"SELECT DISTINCT date FROM {table} ORDER BY date ASC", conn)
    return df["date"].tolist() if not df.empty else []

def _next_trading_dates(calendar: list[str], start_date: str, n: int) -> list[str]:
    if not calendar or n <= 0:
        return []
    try:
        start_idx = calendar.index(str(start_date)[:10])
    except ValueError:
        return []
    end_idx = min(len(calendar), start_idx + 1 + n)
    return calendar[start_idx + 1 : end_idx]

def _calendar_between(calendar: list[str], start_date: str, end_date: str) -> list[str]:
    return [d for d in calendar if start_date <= d <= end_date]

def _compute_signal_for_index(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    idx: int,
) -> bool:
    if idx < 60:
        return False

    # [IMPL] 信号检测逻辑保持与原版一致，确保结果准确性
    high_60 = high[idx - 59 : idx + 1]
    peak_h = float(np.max(high_60))
    peak_bars = 60 - 1 - int(np.argmax(high_60))

    low_120 = low[max(0, idx - 119) : idx + 1]
    s1_low = float(np.min(low_120))
    s1_bars = 120 - 1 - int(np.argmin(low_120))

    s1_done = (s1_bars > peak_bars) and ((peak_h - s1_low) / s1_low > 0.14)
    in_s2 = peak_bars >= 5 and peak_bars <= 55

    box_low = float(np.min(low[idx - peak_bars : idx + 1])) if peak_bars >= 0 else float(low[idx])
    box_shape = (peak_h - box_low) / peak_h < 0.25
    s2_drop = float(close[idx]) <= peak_h * 0.92
    near_bottom = float(close[idx]) <= box_low * 1.05 and float(close[idx]) >= box_low * 0.98

    is_smile = s1_done and in_s2 and box_shape and s2_drop and near_bottom
    is_magic = check_magic(float(low[idx]))
    low_10 = low[max(0, idx - 9) : idx + 1]
    is_new_low = float(low[idx]) == float(np.min(low_10))
    is_valid_candle = float(close[idx]) >= float(open_[idx]) * 0.998

    return is_smile and is_magic and is_new_low and is_valid_candle

def _compute_rsi(series: np.ndarray, period: int = 6) -> np.ndarray:
    """标准 RSI 计算 (与通达信/同花顺算法逻辑接近)"""
    if len(series) < period:
        return np.zeros_like(series)
    delta = np.diff(series)
    delta = np.insert(delta, 0, 0.0)
    up = np.where(delta > 0, delta, 0.0)
    down = np.where(delta < 0, -delta, 0.0)
    
    alpha = 1.0 / period
    def ewm(data):
        res = np.zeros_like(data)
        if len(data) == 0: return res
        curr = data[0]
        res[0] = curr
        for i in range(1, len(data)):
            curr = alpha * data[i] + (1 - alpha) * curr
            res[i] = curr
        return res

    avg_up = ewm(up)
    avg_down = ewm(down)
    denom = avg_up + avg_down
    rsi = np.zeros_like(series)
    rsi[denom > 0] = (avg_up[denom > 0] / denom[denom > 0]) * 100
    return rsi

def _worker_backtest_batch(
    db_path: str,
    table: str,
    codes: list[str],
    query_start: str,
    query_end: str,
    calendar: list[str],
    target_dates: set[str],
    exit_days: int,
    rsi_hook: bool = False,
    vol_shrink: bool = False,
    vol_ratio: float = 1.0,
) -> list[dict]:
    # [IMPL] 返回每笔交易的详细记录：日期,代码,RSI,收益,是否触发移动止损
    trade_records = []
    
    TRAILING_PERCENT = 0.02 # 移动止损间距：2%
    RSI_HOOK_THRESHOLD = 35.0 # 黄金勾低位定义
    
    calendar_idx = {d: i for i, d in enumerate(calendar)}
    conn = sqlite3.connect(db_path)
    try:
        placeholders = ','.join(['?'] * len(codes))
        query = f"""
            SELECT code, date, open, high, low, close, volume
            FROM {table}
            WHERE code IN ({placeholders})
            AND date >= ?
            AND date <= ?
            ORDER BY code, date ASC
        """
        params = codes + [query_start, query_end]
        df_all = pd.read_sql_query(query, conn, params=params)
        
        if df_all.empty:
            return []

        for code, df in df_all.groupby('code'):
            df = df.reset_index(drop=True)
            dates = df["date"].astype(str).tolist()
            date_to_idx = {d: i for i, d in enumerate(dates)}
            open_ = df["open"].to_numpy(dtype=float)
            high = df["high"].to_numpy(dtype=float)
            low = df["low"].to_numpy(dtype=float)
            close = df["close"].to_numpy(dtype=float)
            volume = df["volume"].to_numpy(dtype=float)
            
            # [IMPL] 计算该股票全量的 RSI-6
            rsi_values = _compute_rsi(close, 6)

            for d in dates:
                if d not in target_dates:
                    continue
                idx = date_to_idx.get(d)
                if idx is None or not _compute_signal_for_index(open_, high, low, close, idx):
                    continue

                cal_pos = calendar_idx.get(d)
                if cal_pos is None or cal_pos + 1 >= len(calendar):
                    continue
                
                buy_date = calendar[cal_pos + 1]
                buy_idx = date_to_idx.get(buy_date)
                if buy_idx is None:
                    continue
                
                buy_open = float(open_[buy_idx])
                
                # [IMPL] RSI 黄金勾逻辑检查
                curr_rsi = float(rsi_values[idx])
                if rsi_hook:
                    # 获取昨日索引 (idx - 1)
                    if idx <= 0: continue
                    prev_rsi = float(rsi_values[idx-1])
                    # 规则：今日勾头向上 (curr > prev) 且 昨天还在低位坑里 (< 35)
                    if not (curr_rsi > prev_rsi and prev_rsi < RSI_HOOK_THRESHOLD):
                        continue

                # [IMPL] 成交量缩量逻辑检查
                if vol_shrink:
                    if idx <= 0: continue
                    # 规则：今日成交量 < 昨日成交量 * vol_ratio
                    if volume[idx] >= volume[idx-1] * vol_ratio:
                        continue

                exit_dates = _next_trading_dates(calendar, buy_date, exit_days)
                if not exit_dates:
                    continue
                
                # [IMPL] 严谨回测逻辑 (对齐 A 股 T+1):
                # 1. T+1 (buy_date) 只能买入, 不能卖出, 但要记录 T+1 的最高价用于抬升止损线
                p = 0.0
                buy_high = float(high[buy_idx])
                peak_price = max(buy_open, buy_high)
                triggered_ts = False
                
                # 2. 从 T+2 开始循环检查卖出条件 (exit_dates 包含 T+2, T+3...)
                for i, ed in enumerate(exit_dates):
                    ei = date_to_idx.get(ed)
                    if ei is not None:
                        curr_open = float(open_[ei])
                        curr_high = float(high[ei])
                        curr_low = float(low[ei])
                        curr_close = float(close[ei])
                        
                        stop_price = peak_price * (1 - TRAILING_PERCENT)
                        
                        # 检查止损触发:
                        # a) 如果开盘就低开于止损价下方 (直接吃大面, 止损价卖不掉, 只能开盘逃命)
                        if curr_open <= stop_price:
                            p = (curr_open - buy_open) / buy_open
                            triggered_ts = True
                            break
                        # b) 如果盘中触碰止损价
                        elif curr_low <= stop_price:
                            p = (stop_price - buy_open) / buy_open
                            triggered_ts = True
                            break
                        
                        # 未触发止损, 更新最高价
                        peak_price = max(peak_price, curr_high)
                        
                        # 如果是最后期限 (T+3), 强制以收盘价平仓
                        if i == len(exit_dates) - 1:
                            p = (curr_close - buy_open) / buy_open
                
                trade_records.append({
                    "date": d,
                    "code": code,
                    "rsi_6": round(rsi_values[idx], 2),
                    "profit_pct": round(p * 100, 2),
                    "is_ts": 1 if triggered_ts else 0
                })

    finally:
        conn.close()
    return trade_records

def run_backtest_range(
    db_path: str,
    range_start: str,
    range_end: str,
    exit_days: int,
    workers: int,
    out_csv: str,
    rsi_hook: bool = False,
    vol_shrink: bool = False,
    vol_ratio: float = 1.0,
) -> None:
    conn = sqlite3.connect(db_path)
    table = _pick_kline_table(conn)
    calendar = _get_trading_calendar(conn, table)
    codes = pd.read_sql_query(f"SELECT DISTINCT code FROM {table}", conn)["code"].tolist()
    conn.close()

    if not calendar or not codes:
        print("Error: Empty calendar or codes.")
        return

    target_dates_list = _calendar_between(calendar, range_start, range_end)
    target_dates = set(target_dates_list)
    
    start_dt = datetime.strptime(range_start, "%Y-%m-%d")
    query_start = (start_dt - timedelta(days=300)).strftime("%Y-%m-%d")
    query_end = (datetime.strptime(range_end, "%Y-%m-%d") + timedelta(days=15)).strftime("%Y-%m-%d")

    chunk_size = 100
    code_chunks = [codes[i:i + chunk_size] for i in range(0, len(codes), chunk_size)]
    
    all_trade_records = []

    print(f"Starting Detailed Backtest (Strategy: 2% Trailing Stop + RSI-6, Workers: {workers}, Hook: {rsi_hook}, VolShrink: {vol_shrink}, VolRatio: {vol_ratio})")
    
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _worker_backtest_batch, db_path, table, chunk, query_start, query_end, calendar, target_dates, exit_days, rsi_hook, vol_shrink, vol_ratio
            ): chunk for chunk in code_chunks
        }
        
        pbar = tqdm(total=len(codes), desc="Progress") if tqdm else None
        for future in as_completed(futures):
            records = future.result()
            all_trade_records.extend(records)
            if pbar: pbar.update(len(futures[future]))
        if pbar:
            pbar.close()

    if not all_trade_records:
        print("No signals found in this range.")
        return

    df_out = pd.DataFrame(all_trade_records)
    df_out = df_out.sort_values(by=["date", "code"])
    df_out.to_csv(out_csv, index=False, encoding="utf-8-sig")

    print(f"\n--- 详细交易统计 (Trailing Stop: 2%) ---")
    avg_p = df_out["profit_pct"].mean()
    ts_rate = df_out["is_ts"].mean()
    avg_rsi = df_out["rsi_6"].mean()
    print(f"信号总数: {len(df_out)}")
    print(f"平均选股 RSI-6: {avg_rsi:.2f}")
    print(f"全局平均单笔收益: {avg_p:.2f}%")
    print(f"移动止损触发率 (TS): {ts_rate:.2%}")
    if rsi_hook:
        print(f"黄金勾过滤生效: 已自动剔除趋势不符或非低位信号")
    print(f"详细个股结果已保存至 {out_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--range-start", help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--range-end", help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--target-date", help="指定单日回测 (YYYY-MM-DD)")
    parser.add_argument("--workers", type=int, default=os.cpu_count())
    parser.add_argument("--exit-days", type=int, default=2)
    parser.add_argument("--out", default="result.csv")
    parser.add_argument("--rsi-hook", action="store_true", help="仅保留 RSI 低位勾头信号 (RSI<35 且今日>昨日)")
    parser.add_argument("--vol-shrink", action="store_true", help="仅保留今日成交量小于昨日的信号 (缩量)")
    parser.add_argument("--vol-ratio", type=float, default=1.0, help="缩量比例阈值 (例如 0.8 表示今日成交量需小于昨日的 80%%)")
    args = parser.parse_args()

    # 逻辑处理：单日模式或范围模式
    r_start = args.range_start
    r_end = args.range_end
    
    if args.target_date:
        r_start = args.target_date
        r_end = args.target_date
    
    if not r_start or not r_end:
        parser.error("必须提供 --target-date 或同时提供 --range-start 与 --range-end")

    run_backtest_range(
        db_path=DB_PATH,
        range_start=r_start,
        range_end=r_end,
        exit_days=args.exit_days,
        workers=args.workers,
        out_csv=args.out,
        rsi_hook=args.rsi_hook,
        vol_shrink=args.vol_shrink,
        vol_ratio=args.vol_ratio
    )
