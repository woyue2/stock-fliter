#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取个股资金流向数据 - 使用 AkShare

资金流向字段：
- 超大单净流入：机构特大单
- 大单净流入：主力大单
- 中单净流入：散户中单
- 小单净流入：散户小单
- 主力净流入：超大单+大单合计

使用方法：
python fetch_fund_flow.py --code 600519
python fetch_fund_flow.py --codes 600519,000001,300001
python fetch_fund_flow.py --test
python fetch_fund_flow.py --all --sample 50
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd

try:
    import akshare as ak
except ImportError:
    print("请先安装: pip install akshare")
    sys.exit(1)

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from util.progress import ProgressBar

# 配置
FUNDFLOW_DIR = Path(__file__).resolve().parent / "data" / "fundflow"

# 列名映射（原始中文 -> 保存的列名）
COLUMN_MAPPING = {
    "日期": "date",
    "收盘价": "close",
    "涨跌幅": "pct_chg",
    "主力净流入-净额": "main_force_net",
    "主力净流入-净占比": "main_force_pct",
    "超大单净流入-净额": "super_large_net",
    "超大单净流入-净占比": "super_large_pct",
    "大单净流入-净额": "large_net",
    "大单净流入-净占比": "large_pct",
    "中单净流入-净额": "medium_net",
    "中单净流入-净占比": "medium_pct",
    "小单净流入-净额": "small_net",
    "小单净流入-净占比": "small_pct",
}


def get_market(code: str) -> str:
    """根据股票代码判断市场"""
    return "sh" if code.startswith("6") else "sz"


def get_stock_list() -> List[str]:
    """获取A股股票列表，API失败时从本地数据目录获取"""
    # 首先尝试从AkShare获取
    for attempt in range(3):
        try:
            stock_list = ak.stock_info_a_code_name()
            codes = stock_list["code"].tolist()
            result = [c for c in codes if c.startswith(("0", "3", "6"))]
            if result:
                return result
        except Exception as e:
            if attempt < 2:
                time.sleep(1)
            continue

    # API失败，从本地数据目录获取
    print("  API获取失败，尝试从本地数据目录获取...")
    raw_dir = Path(__file__).resolve().parent / "data" / "raw"
    if raw_dir.exists():
        codes = [f.stem for f in raw_dir.glob("*.csv") if f.stem.startswith(("0", "3", "6"))]
        if codes:
            print(f"  从本地找到 {len(codes)} 只股票")
            return sorted(codes)

    print("  无法获取股票列表")
    return []


def fetch_fund_flow_data(code: str) -> Optional[pd.DataFrame]:
    """
    获取单只股票的资金流向数据，带重试机制

    Args:
        code: 股票代码 (如 600519)

    Returns:
        DataFrame 或 None
    """
    market = get_market(code)

    for attempt in range(3):
        try:
            df = ak.stock_individual_fund_flow(stock=code, market=market)

            if df is None or df.empty:
                return None

            # 选择API返回的所有原始列（在COLUMN_MAPPING中定义的）
            source_columns = list(COLUMN_MAPPING.keys())
            available_cols = [c for c in source_columns if c in df.columns]
            df = df[available_cols].copy()

            # 重命名列
            df = df.rename(columns=COLUMN_MAPPING)

            # 添加 code 列
            df["code"] = code

            # 转换日期格式
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

            # 确保数值列为 float（除 date 和 code 外的所有列）
            numeric_cols = [c for c in df.columns if c not in ["date", "code"]]
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            # 按日期升序排序
            df = df.sort_values("date").reset_index(drop=True)

            return df

        except Exception:
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))  # 指数退避: 0.5s, 1s
            continue

    return None


def load_existing_data(code: str) -> Optional[pd.DataFrame]:
    """加载已存在的资金流向数据"""
    file_path = FUNDFLOW_DIR / f"{code}.csv"
    if not file_path.exists():
        return None

    try:
        df = pd.read_csv(file_path)
        if df.empty:
            return None
        return df
    except Exception:
        return None


def merge_data(existing_df: Optional[pd.DataFrame], new_df: pd.DataFrame) -> pd.DataFrame:
    """合并新旧数据，去重保留最新"""
    if existing_df is None or existing_df.empty:
        return new_df

    # 合并
    combined = pd.concat([existing_df, new_df], ignore_index=True)

    # 去重：按 date + code 去重，保留最后出现的（最新的）
    combined = combined.drop_duplicates(subset=["date", "code"], keep="last")

    # 按日期排序
    combined = combined.sort_values("date").reset_index(drop=True)

    return combined


def save_data(df: pd.DataFrame, code: str) -> Path:
    """保存数据到 CSV"""
    FUNDFLOW_DIR.mkdir(parents=True, exist_ok=True)
    file_path = FUNDFLOW_DIR / f"{code}.csv"
    df.to_csv(file_path, index=False, encoding="utf-8-sig")
    return file_path


def get_last_date(code: str) -> Optional[str]:
    """获取已有数据的最新日期"""
    file_path = FUNDFLOW_DIR / f"{code}.csv"
    if not file_path.exists():
        return None

    try:
        # 快速读取最后一行
        df = pd.read_csv(file_path, usecols=["date"])
        if df.empty:
            return None
        return df["date"].iloc[-1]
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(
        description="获取个股资金流向数据（特大单/大单/中单/小单）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 获取单只股票
  python fetch_fund_flow.py --code 600121

  # 获取多只股票
  python fetch_fund_flow.py --codes 600121,000001,300001

  # 测试模式（10只随机股票）
  python fetch_fund_flow.py --test

  # 全市场采样
  python fetch_fund_flow.py --all --sample 50

  # 全市场（耗时较长）
  python fetch_fund_flow.py --all
        """,
    )

    parser.add_argument("--code", "-c", type=str, help="股票代码")
    parser.add_argument("--codes", type=str, help="逗号分隔的股票代码列表")
    parser.add_argument("--all", action="store_true", help="全市场扫描")
    parser.add_argument("--test", action="store_true", help="测试模式（10只随机股票）")
    parser.add_argument("--sample", type=int, help="随机采样数量")
    parser.add_argument(
        "--delay", type=float, default=0.1, help="请求间隔秒数（默认：0.1）"
    )

    args = parser.parse_args()

    if not args.all and not args.code and not args.codes and not args.test:
        parser.error("必须指定 --code, --codes, --test 或 --all")

    # 确保输出目录存在
    FUNDFLOW_DIR.mkdir(parents=True, exist_ok=True)

    # 确定股票列表
    if args.code:
        codes = [args.code]
    elif args.codes:
        codes = [c.strip() for c in args.codes.split(",")]
    elif args.test:
        print("测试模式：获取10只随机股票")
        all_codes = get_stock_list()
        import random
        random.seed(42)
        codes = random.sample(all_codes, min(10, len(all_codes)))
    elif args.all:
        print("\n获取股票列表...")
        codes = get_stock_list()
        print(f"找到 {len(codes)} 只股票")

        if args.sample:
            import random
            random.seed(42)
            codes = random.sample(codes, min(args.sample, len(codes)))

    print("=" * 60)
    print("资金流向数据获取")
    print("=" * 60)
    print(f"股票数量: {len(codes)}")
    print(f"输出目录: {FUNDFLOW_DIR}")
    print(f"数据字段: 超大单/大单/中单/小单/主力净流入")
    print("=" * 60)

    # 获取数据
    success = 0
    fail = 0
    skipped = 0

    with ProgressBar(total=len(codes), desc="获取进度") as pbar:
        for i, code in enumerate(codes):
            # 检查是否需要更新
            last_date = get_last_date(code)

            # 获取新数据
            new_df = fetch_fund_flow_data(code)

            if new_df is not None and not new_df.empty:
                # 检查是否已有最新数据
                latest_date = new_df["date"].iloc[-1] if not new_df.empty else None

                if last_date and latest_date and last_date >= latest_date:
                    skipped += 1
                    pbar.update(1, success=True)
                    continue

                # 加载现有数据并合并
                existing_df = load_existing_data(code)
                merged_df = merge_data(existing_df, new_df)

                # 保存
                save_data(merged_df, code)

                if last_date:
                    new_records = len(new_df[new_df["date"] > last_date])
                    print(f"\n  ✓ {code}: +{new_records} 条新数据 (总计: {len(merged_df)})")
                else:
                    print(f"\n  ✓ {code}: 新增 {len(merged_df)} 条数据")

                success += 1
            else:
                fail += 1
                print(f"\n  ✗ {code}: 获取失败")

            pbar.update(1, success=(new_df is not None))

            # 请求间隔
            if args.delay > 0:
                time.sleep(args.delay)

    print("\n" + "=" * 60)
    print(f"完成！成功: {success}, 跳过: {skipped}, 失败: {fail}")
    print(f"数据保存至: {FUNDFLOW_DIR}")

    # 显示样本数据
    if success > 0:
        sample_code = codes[0]
        sample_file = FUNDFLOW_DIR / f"{sample_code}.csv"
        if sample_file.exists():
            df = pd.read_csv(sample_file)
            print(f"\n【{sample_code} 样本数据 - 最新5条】")
            print(df.tail().to_string(index=False))

    return 0


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
