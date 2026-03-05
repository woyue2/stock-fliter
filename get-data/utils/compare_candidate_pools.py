# -*- coding: utf-8 -*-
"""
[L3] compare_candidate_pools.py
[ROLE]: 比较最近两次选股候选池快照，追踪标的变化
[INPUT]: data/candidates/candidates_*.csv
[OUTPUT]: stdout 差异详情
[PROTOCOL]: 变更时更新此头部，然后检查 L2/CLAUDE.md

比较最近两次候选池快照，列出新进/退出的股票。
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = BASE_DIR / "data" / "candidates"


def list_snapshots() -> List[Path]:
    """列出所有候选池快照文件，按文件名排序（即时间顺序）。"""
    if not SNAPSHOT_DIR.exists():
        return []
    return sorted(
        [p for p in SNAPSHOT_DIR.glob("candidates_*.csv") if p.is_file()],
        key=lambda p: p.name,
    )


def load_pool(path: Path) -> pd.DataFrame:
    """加载单次候选池快照，只保留 code/name 并去重。"""
    df = pd.read_csv(path, dtype={"code": str})
    if "code" not in df.columns:
        raise ValueError(f"文件缺少 code 列: {path}")
    if "name" not in df.columns:
        df["name"] = ""

    df["code"] = df["code"].astype(str).str.zfill(6)
    df["name"] = df["name"].astype(str)
    return df[["code", "name"]].drop_duplicates()


def compare_two(prev_path: Path, curr_path: Path) -> None:
    """比较两次快照，打印新进/退出的股票列表。"""
    prev_df = load_pool(prev_path)
    curr_df = load_pool(curr_path)

    prev_codes = set(prev_df["code"])
    curr_codes = set(curr_df["code"])

    new_codes = sorted(curr_codes - prev_codes)
    gone_codes = sorted(prev_codes - curr_codes)

    print("=" * 60)
    print("候选池规模变化")
    print("-" * 60)
    print(f"上一次: {prev_path.name} (股票数: {len(prev_codes)})")
    print(f"本次  : {curr_path.name} (股票数: {len(curr_codes)})")
    delta = len(curr_codes) - len(prev_codes)
    sign = "+" if delta >= 0 else "-"
    print(f"变化   : {sign}{abs(delta)} 只\n")

    print("⭐ 新进入候选池的股票:")
    if new_codes:
        new_df = curr_df[curr_df["code"].isin(new_codes)].sort_values("code")
        print(f"共 {len(new_codes)} 只：")
        for _, row in new_df.iterrows():
            print(f"  {row['code']}  {row['name']}")
    else:
        print("  无")

    print("\n⚠️ 退出候选池的股票:")
    if gone_codes:
        gone_df = prev_df[prev_df["code"].isin(gone_codes)].sort_values("code")
        print(f"共 {len(gone_codes)} 只：")
        for _, row in gone_df.iterrows():
            print(f"  {row['code']}  {row['name']}")
    else:
        print("  无")


def main() -> int:
    snapshots = list_snapshots()
    if len(snapshots) < 2:
        print("⚠️ 候选池快照文件少于 2 个，无法比较。")
        print("   请至少在全量模式下运行两次 `python get-data/fetch_daily_history.py --all` 以生成快照。")
        return 1

    prev_path, curr_path = snapshots[-2], snapshots[-1]
    print("即将比较最近两次候选池快照：")
    print(f"  上一次: {prev_path}")
    print(f"  本次  : {curr_path}\n")

    compare_two(prev_path, curr_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

