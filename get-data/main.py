# # -*- coding: utf-8 -*-


"""
获取A股日K数据（增量更新 + 随机10只样本/全市场扫描）

数据源：
- 主：BaoStock（免费）
- 备：Tencent K线接口（免费，稳定性较低）

输出：
- data/raw/{code}.csv (累计历史数据，不覆盖旧数据)
- data/selected_stocks.csv (本次选中的股票)
- output/fetch_summary_YYYYMMDD_HHMMSS.csv (本次拉取摘要)
"""
from __future__ import annotations

import argparse
import importlib
import random
import sys
import time

# Force UTF-8 output for Windows to support emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        # Use 'replace' error handler to avoid UnicodeEncodeError on Windows GBK terminals
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
import requests

# 添加 util 目录到路径
util_dir = Path(__file__).resolve().parent.parent / "util"
if str(util_dir) not in sys.path:
    sys.path.append(str(util_dir))

from progress import print_progress, ProgressBar


# ... (保留前文导入)
# 添加 util 目录到路径
util_dir = Path(__file__).resolve().parent.parent / "util"
if str(util_dir) not in sys.path:
    sys.path.append(str(util_dir))

try:
    from progress import print_progress, ProgressBar
except ImportError:
    # 兼容性回退
    def print_progress(*args, **kwargs):
        pass
    class ProgressBar:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def update(self, *args, **kwargs): pass

DEFAULT_DAYS = 365
DEFAULT_SAMPLE_SIZE = 10
DEFAULT_SEED = 42
SUSPENDED_MAX_STALE_DAYS = 7
BATCH_SIZE = 100  # 批次大小（进度条显示用）


@dataclass
class StockItem:
    code: str
    name: str
    bs_code: str


_BAOSTOCK_MODULE = None


def ensure_dirs(base_dir: Path) -> Tuple[Path, Path, Path]:
    data_dir = base_dir / "data"
    raw_dir = data_dir / "raw"
    output_dir = base_dir / "output"
    data_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    return data_dir, raw_dir, output_dir


def get_baostock():
    global _BAOSTOCK_MODULE
    if _BAOSTOCK_MODULE is None:
        try:
            _BAOSTOCK_MODULE = importlib.import_module("baostock")
        except Exception as exc:
            raise RuntimeError("未安装 baostock，请先安装依赖：pip install baostock") from exc
    return _BAOSTOCK_MODULE


def login_baostock() -> None:
    bs = get_baostock()
    lg = bs.login()
    if lg.error_code != "0":
        msg = f"BaoStock 登录失败: {lg.error_msg}"
        print(f"提示: 如果遇到网络连接问题，请运行根目录下的 'python diagnose.py' 进行诊断。")
        raise RuntimeError(msg)


def logout_baostock() -> None:
    try:
        bs = get_baostock()
        bs.logout()
    except Exception:
        pass


def fetch_stock_basic() -> pd.DataFrame:
    bs = get_baostock()
    rs = bs.query_stock_basic()
    if rs.error_code != "0":
        raise RuntimeError(f"BaoStock 获取股票列表失败: {rs.error_msg}")

    rows = []
    while rs.next():
        rows.append(rs.get_row_data())

    df = pd.DataFrame(rows, columns=rs.fields)
    return df


def normalize_stock_basic(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "code_name" in df.columns and "name" not in df.columns:
        df = df.rename(columns={"code_name": "name"})

    if "code" not in df.columns or "name" not in df.columns:
        raise ValueError("股票列表缺少必要字段: code/name")

    df["exchange"] = df["code"].str.split(".").str[0]
    df["symbol"] = df["code"].str.split(".").str[1]
    return df


def is_st_or_delisted_name(name: str) -> bool:
    name = str(name).upper()
    return "ST" in name or "退" in name


def filter_active_a_shares(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_stock_basic(df)
    today = pd.Timestamp(datetime.now().date())

    records = []
    for row in df.itertuples(index=False):
        row_dict = row._asdict()
        exchange = str(row_dict.get("exchange", ""))
        symbol = str(row_dict.get("symbol", ""))
        name = str(row_dict.get("name", ""))

        if exchange not in {"sh", "sz"}:
            continue
        if len(symbol) != 6:
            continue

        status = str(row_dict.get("status", "1"))
        if status not in {"1", "1.0"}:
            continue

        out_date_raw = row_dict.get("outDate", "")
        if out_date_raw:
            out_date = pd.to_datetime(out_date_raw, errors="coerce")
            if pd.notna(out_date) and out_date <= today:
                continue

        type_value = str(row_dict.get("type", "1"))
        if type_value not in {"1", "1.0"}:
            continue

        if is_st_or_delisted_name(name):
            continue

        records.append(row_dict)

    if not records:
        return df.iloc[0:0].copy()
    return pd.DataFrame.from_records(records)


def load_existing(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
    except Exception:
        return None
    
    df = normalize_code_column(df)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df


def normalize_code_column(df: pd.DataFrame) -> pd.DataFrame:
    if "code" not in df.columns:
        return df
    df = df.copy()

    def _normalize_code(value: object) -> str:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return ""
        text = str(value).strip()
        if "." in text:
            text = text.split(".")[-1]
        text = "".join(ch for ch in text if ch.isdigit())
        if not text:
            return ""
        return text.zfill(6)

    df["code"] = df["code"].map(_normalize_code)
    return df


def compute_fetch_range(existing_df: Optional[pd.DataFrame], days: int) -> Tuple[str, str]:
    end_date = datetime.now().strftime("%Y-%m-%d")
    if existing_df is None or existing_df.empty:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return start_date, end_date

    last_date_series = pd.to_datetime(existing_df["date"], errors="coerce")
    last_date = last_date_series.max()
    if pd.isna(last_date):
        start_date_dt = datetime.now() - timedelta(days=days)
    else:
        start_date_dt = pd.Timestamp(last_date) + timedelta(days=1)
    start_date = start_date_dt.strftime("%Y-%m-%d")
    return start_date, end_date


def parse_baostock_rows(rows: List[List[str]], fields: List[str]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=fields)
    df["date"] = pd.to_datetime(df["date"])
    for col in ["open", "high", "low", "close", "volume", "amount", "pctChg"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = normalize_code_column(df)
    return df


def fetch_baostock_daily(bs_code: str, start_date: str, end_date: str) -> Tuple[pd.DataFrame, Optional[str]]:
    bs = get_baostock()
    rs = bs.query_history_k_data_plus(
        code=bs_code,
        fields="date,code,open,high,low,close,volume,amount,pctChg,tradestatus",
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="2",
    )

    if rs.error_code != "0":
        return pd.DataFrame(), rs.error_msg

    rows = []
    while rs.next():
        rows.append(rs.get_row_data())

    df = parse_baostock_rows(rows, rs.fields)
    return df, None


def fetch_tencent_daily(code: str, count: int = DEFAULT_DAYS) -> pd.DataFrame:
    prefix = "sh" if code.startswith("6") else "sz"
    symbol = f"{prefix}{code}"
    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,{count},qfq"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    payload = resp.json()
    day_rows = payload.get("data", {}).get(symbol, {}).get("day", [])
    if not day_rows:
        return pd.DataFrame()

    df = pd.DataFrame(day_rows, columns=["date", "open", "close", "high", "low", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["amount"] = None
    df["pctChg"] = None
    df["tradestatus"] = None
    return df


def merge_and_save(existing_df: Optional[pd.DataFrame], new_df: pd.DataFrame, path: Path) -> pd.DataFrame:
    frames = [df for df in [existing_df, new_df] if isinstance(df, pd.DataFrame) and not df.empty]
    if not frames:
        empty_df = pd.DataFrame()
        empty_df.to_csv(path, index=False, encoding="utf-8-sig")
        return empty_df

    combined_df = pd.DataFrame(pd.concat(frames, ignore_index=True))
    combined_df = normalize_code_column(combined_df)
    if "date" in combined_df.columns:
        sorted_df = combined_df.sort_values(by="date")
        date_series = sorted_df["date"]
        dedup_df = sorted_df.loc[~date_series.duplicated(keep="last")].copy()

        def _format_date(value) -> str:
            dt = pd.to_datetime(value, errors="coerce")
            if pd.isna(dt):
                return ""
            return pd.Timestamp(dt).strftime("%Y-%m-%d")

        dedup_df["date"] = dedup_df["date"].map(_format_date)
        combined_df = dedup_df
    combined_df.to_csv(path, index=False, encoding="utf-8-sig")
    return combined_df


def is_recent_trading_date(latest_date: pd.Timestamp) -> bool:
    if pd.isna(latest_date):
        return False
    return (datetime.now() - latest_date).days <= SUSPENDED_MAX_STALE_DAYS


def select_stocks(
    stock_df: pd.DataFrame,
    sample_size: int,
    seed: int,
    selected_path: Path,
    resample: bool,
    use_all: bool = False,
) -> List[StockItem]:
    if use_all:
        return [
            StockItem(code=row.symbol, name=row.name, bs_code=row.code)
            for row in stock_df.itertuples(index=False)
        ]

    if selected_path and selected_path.exists() and not resample:
        try:
            selected_df = pd.read_csv(selected_path, dtype={"code": str, "bs_code": str})
        except ValueError:
            selected_df = pd.read_csv(selected_path)
            if "code" in selected_df.columns:
                selected_df["code"] = selected_df["code"].astype(str).str.zfill(6)
        
        required_cols = {"code", "name", "bs_code"}
        if required_cols.issubset(selected_df.columns):
            if "code" in selected_df.columns:
                 selected_df["code"] = selected_df["code"].astype(str).str.zfill(6)
            return [
                StockItem(code=str(row.code).zfill(6), name=row.name, bs_code=row.bs_code)
                for row in selected_df.itertuples(index=False)
            ]

    candidates = [
        StockItem(code=row.symbol, name=row.name, bs_code=row.code)
        for row in stock_df.itertuples(index=False)
    ]

    rng = random.Random(seed)
    rng.shuffle(candidates)
    return candidates[: sample_size]


    # 删除旧的 print_progress 函数



def get_last_date_fast(path: Path) -> Optional[pd.Timestamp]:
    """快速读取CSV文件最后一行获取日期，避免读取整个文件"""
    if not path.exists():
        return None
    try:
        with open(path, 'rb') as f:
            f.seek(0, 2)  # Seek to end
            filesize = f.tell()
            if filesize == 0:
                return None

            # 读取最后 256 字节通常足够覆盖一行
            offset = min(filesize, 256)
            f.seek(-offset, 2)
            block = f.read()

            # 解码，忽略开头可能的截断字符
            text = block.decode('utf-8-sig', errors='ignore')
            lines = text.strip().splitlines()
            if not lines:
                return None

            last_line = lines[-1]
            if "," not in last_line:
                return None
            
            # 假设第一列是 date
            date_str = last_line.split(",")[0]
            # 简单的格式校验
            if len(date_str) < 8: 
                return None
            
            dt = pd.to_datetime(date_str, errors='coerce')
            if pd.isna(dt):
                return None
            return dt
    except Exception:
        return None


def check_local_data_date(raw_dir: Path) -> Optional[pd.Timestamp]:
    """检查本地数据最新日期（采样前5个文件）"""
    if not raw_dir.exists():
        return None
    
    count = 0
    max_date = None
    
    # 简单的遍历，只看前5个有效文件
    for csv_file in raw_dir.glob("*.csv"):
        dt = get_last_date_fast(csv_file)
        if dt:
            if max_date is None or dt > max_date:
                max_date = dt
            count += 1
            if count >= 5:
                break
    return max_date


def main() -> int:
    parser = argparse.ArgumentParser(
        description="A股数据获取（BaoStock + Tencent 备用，带进度条）",
        epilog="""
运行模式（三选一，默认全量）:
  无参数           全量获取/扫描
  --test           测试模式，10 只股票
  --random-test    随机测试，50 只股票
        """,
    )
    parser.add_argument("--test", "-t", action="store_true", help="测试模式，10 只股票")
    parser.add_argument("--random-test", action="store_true", help="随机测试，50 只股票")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="最近天数（默认365）")
    parser.add_argument("--sample-size", type=int, default=None, help="[高级] 覆盖随机样本数（与 --test/--random-test 配合时慎用）")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="随机种子（默认42）")
    parser.add_argument("--resample", action="store_true", help="[高级] 重新随机选择股票")
    parser.add_argument("--all", "-all", action="store_true", help="[高级] 显式全量扫描")
    args = parser.parse_args()

    # 运行模式：默认全量；--random-test 优先于 --test；显式 --all 强制全量
    if args.all:
        use_all = True
        sample_size = DEFAULT_SAMPLE_SIZE
        resample = False
    elif args.random_test:
        use_all = False
        sample_size = 50
        resample = True
    elif args.test:
        use_all = False
        sample_size = 10
        resample = False
    else:
        use_all = True
        sample_size = DEFAULT_SAMPLE_SIZE
        resample = False
    if args.sample_size is not None:
        sample_size = args.sample_size
    if args.random_test or args.test:
        resample = args.resample or (args.random_test and True)

    base_dir = Path(__file__).resolve().parent
    data_dir, raw_dir, output_dir = ensure_dirs(base_dir)
    selected_path = data_dir / "selected_stocks.csv"
    selected_all_path = data_dir / "selected_stocks_all.csv"
    summary_path = output_dir / f"fetch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    # 显示本地数据状态
    local_date = check_local_data_date(raw_dir)
    if local_date:
        print(f"[状态] 本地数据最新日期: {local_date.strftime('%Y-%m-%d')}")
    else:
        print(f"[状态] 本地暂无数据或无法识别日期")

    print("[数据] 登录 BaoStock...")
    login_baostock()
    try:
        stock_basic = fetch_stock_basic()
    finally:
        logout_baostock()

    stock_filtered = filter_active_a_shares(stock_basic)

    candidates = select_stocks(
        stock_filtered,
        sample_size,
        args.seed,
        selected_all_path if use_all else selected_path,
        resample,
        use_all=use_all
    )
    total_candidates = len(candidates)
    print(f"[数据] 候选池数量: {total_candidates}")

    selected: List[StockItem] = []
    summary_rows = []
    
    # 记录全局最新日期
    global_max_date = None

    print("[数据] 开始获取数据...")
    start_time = time.time()
    success_count = 0
    failed_count = 0
    skipped_count = 0 # 统计跳过数量

    login_baostock()
    try:
        # 计算本次运行的目标截止日期（通常是今天）
        target_end_date_str = datetime.now().strftime("%Y-%m-%d")
        
        with ProgressBar(total_candidates, desc="获取进度") as pbar:
            for idx, item in enumerate(candidates, 1):
                if not use_all and len(selected) >= sample_size:
                    break

                path = raw_dir / f"{item.code}.csv"
                
                # --- 快速断点检测 ---
                # 如果文件存在且最后一条日期已经是最新的，则直接跳过读取和请求
                fast_latest_date = get_last_date_fast(path)
                if fast_latest_date:
                     # 更新全局日期
                    if global_max_date is None or fast_latest_date > global_max_date:
                        global_max_date = fast_latest_date
                    
                    if fast_latest_date.strftime("%Y-%m-%d") >= target_end_date_str:
                        # 已是最新，直接跳过
                        selected.append(item)
                        success_count += 1
                        skipped_count += 1
                        pbar.update(1, success=True)
                        summary_rows.append({
                            "code": item.code,
                            "name": item.name,
                            "source": "local_fast_check",
                            "status": "ok_skipped",
                            "row_count": 0,
                            "latest_date": fast_latest_date.strftime("%Y-%m-%d"),
                            "error": "",
                        })
                        continue
                # ------------------

                existing_df = load_existing(path)
                start_date, end_date = compute_fetch_range(existing_df, args.days)

                new_df = pd.DataFrame()
                error_msg = None
                source = "none"
                
                # 尝试 BaoStock
                if start_date <= end_date:
                    new_df, error_msg = fetch_baostock_daily(item.bs_code, start_date, end_date)
                    source = "baostock"

                # 如果 BaoStock 失败或无数据，尝试 Tencent
                # 修改逻辑：只要 new_df 为空就尝试 Tencent，不仅限于有 error_msg 的情况
                baostock_failed = new_df is None or new_df.empty
                if baostock_failed and start_date <= end_date:
                    bs_error = error_msg if error_msg else "无数据返回"
                    # 清除当前行（进度条），打印重试信息
                    sys.stdout.write("\r" + " " * 100 + "\r")
                    print(f"[重试] {item.code} {item.name}: BaoStock 异常 ({bs_error}) -> 尝试腾讯接口")
                    
                    try:
                        new_df = fetch_tencent_daily(item.code, count=args.days)
                        source = "tencent"
                        error_msg = None # 重置错误信息，因为腾讯可能成功
                        if new_df is None or new_df.empty:
                            error_msg = "腾讯接口也未返回数据"
                    except Exception as exc:
                        error_msg = f"腾讯接口报错: {str(exc)}"

                row_count = 0
                status = "failed"
                merged_df = None
                if new_df is not None and not new_df.empty:
                    new_df = new_df.copy()
                    new_df["code"] = item.code
                    new_df["source"] = source
                    merged_df = merge_and_save(existing_df, new_df, path)
                    row_count = len(new_df)
                    status = "ok"
                elif existing_df is not None and not existing_df.empty:
                    row_count = len(existing_df)
                    status = "ok"
                    merged_df = existing_df
                
                latest_date = None
                if status == "ok":
                    latest_source = merged_df if merged_df is not None else existing_df
                    latest_series = pd.to_datetime(latest_source["date"], errors="coerce") if latest_source is not None else pd.Series([])
                    latest_date = latest_series.max()
                    
                    if pd.notna(latest_date):
                        if global_max_date is None or latest_date > global_max_date:
                            global_max_date = latest_date
                    
                    if not is_recent_trading_date(latest_date):
                        status = "skipped_suspended"
                
                if status == "ok":
                    selected.append(item)
                    success_count += 1
                    pbar.update(1, success=True)
                else:
                    failed_count += 1
                    pbar.update(1, success=False)
                    # 打印失败详情
                    sys.stdout.write("\r" + " " * 100 + "\r")
                    fail_reason = error_msg if error_msg else "未知原因 (无数据)"
                    print(f"[失败] {item.code} {item.name}: {source} 接口失败. 原因: {fail_reason}")

                summary_rows.append({
                    "code": item.code,
                    "name": item.name,
                    "source": source,
                    "status": status,
                    "row_count": row_count,
                    "latest_date": latest_date.strftime("%Y-%m-%d") if latest_date is not None and pd.notna(latest_date) else "",
                    "error": error_msg or "",
                })

    finally:
        logout_baostock()

    elapsed = time.time() - start_time
    print(f"\n[OK] 获取完成！耗时: {elapsed:.1f}秒")
    print(f"[统计] 总计: {total_candidates} | 成功: {success_count} (跳过: {skipped_count}) | 失败: {failed_count}")
    
    if global_max_date:
        print(f"[数据] 数据最新日期: {global_max_date.strftime('%Y-%m-%d')}")

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")

    if not use_all and len(selected) < sample_size:
        print(f"[X] 有效股票不足 {sample_size} 只（实际 {len(selected)} 只）")
        return 1

    selected_df = pd.DataFrame([
        {"code": item.code, "name": item.name, "bs_code": item.bs_code}
        for item in selected
    ])
    output_selected_path = selected_all_path if use_all else selected_path
    selected_df.to_csv(output_selected_path, index=False, encoding="utf-8-sig")

    print(f"[OK] 完成：已获取 {len(selected)} 只股票数据")
    if use_all:
        print(f"[OK] 全市场扫描模式，共 {total_candidates} 只候选，已处理 {len(selected)} 只有效股票")
    print(f"[OK] 股票列表：{output_selected_path}")
    print(f"[OK] 拉取摘要：{summary_path}")
    return 0

# 手动运行
# import os
# # 注意：使用 os.system 时，命令是作为一个字符串传递的
# os.system("python /home/aa/Park/stock-fliter/get-data/update_industry.py")

if __name__ == "__main__":
    raise SystemExit(main())



