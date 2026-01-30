#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
玄学 + 134 组合命中率分析脚本（扩展版）
分析各种组合的筛选效果，生成股票推荐报告
支持优先级：回调买点（6连阳后阴线）> 追涨买点（第6天阳线）> 其他
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

from mystic_indicators import get_mystic_priority

OUTPUT_DIR = Path(__file__).parent / "output"


def read_csv_utf8(path: Path) -> pd.DataFrame:
    """读取 CSV（自动处理编码）"""
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb2312"):
        try:
            return pd.read_csv(path, encoding=enc, dtype=str)
        except Exception:
            continue
    return pd.DataFrame()


def get_latest_file(pattern: str) -> Path | None:
    """获取最新的文件（按修改时间排序）"""
    files = list(OUTPUT_DIR.glob(pattern))
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def to_bool(val) -> bool:
    """转换为布尔值"""
    if val is None or pd.isna(val):
        return False
    text = str(val).strip().lower()
    return text in {"true", "1", "yes", "是"}


def get_priority_label(row: pd.Series) -> str:
    """获取优先级标签
    
    优先级说明:
    - [STAR]买入: 6连阳后阴线，最佳买入时机
    - [STAR]等待: 第6天阳线，等明天回调再买
    """
    # 支持新旧两种列名
    down = to_bool(row.get("回调买点", False)) or to_bool(row.get("今天为跌且7天刚好6涨1跌", False))
    up = to_bool(row.get("等待买点", False)) or to_bool(row.get("追涨买点", False)) or to_bool(row.get("今天为涨且7天刚好6涨1跌", False))
    if down:
        return "[STAR]买入"
    if up:
        return "[STAR]等待"
    return ""


def analyze_combinations():
    """分析各组合的命中情况"""
    print("=" * 70)
    print("[CHART] 玄学 + 组合条件 命中率分析（扩展版）")
    print("=" * 70)
    
    # 定义所有组合类型
    combos = {
        "xuanxue_134_61": ("玄学61 + 稳步上升(1) + 趋势(3) + 网格(4)", "134"),
        "xuanxue_134_6": ("玄学6 + 稳步上升(1) + 趋势(3) + 网格(4)", "134"),
        "xuanxue_13_61": ("玄学61 + 稳步上升(1) + 趋势(3)", "13"),
        "xuanxue_13_6": ("玄学6 + 稳步上升(1) + 趋势(3)", "13"),
        "xuanxue_34_61": ("玄学61 + 趋势(3) + 网格(4)", "34"),
        "xuanxue_34_6": ("玄学6 + 趋势(3) + 网格(4)", "34"),
        "xuanxue_14_61": ("玄学61 + 稳步上升(1) + 网格(4)", "14"),
        "xuanxue_14_6": ("玄学6 + 稳步上升(1) + 网格(4)", "14"),
        "xuanxue_1_61": ("玄学61 + 稳步上升(1)", "1"),
        "xuanxue_1_6": ("玄学6 + 稳步上升(1)", "1"),
        "xuanxue_4_61": ("玄学61 + 网格(4)", "4"),
        "xuanxue_4_6": ("玄学6 + 网格(4)", "4"),
    }
    
    results = {}
    all_stocks = {}
    
    for combo_name, (combo_desc, combo_type) in combos.items():
        pattern = f"{combo_name}_*只_baseon_*.csv"
        latest = get_latest_file(pattern)
        
        if latest:
            df = read_csv_utf8(latest)
            count = len(df)
            
            today_down = 0
            today_up = 0
            # 支持新旧多种列名
            down_col = "回调买点" if "回调买点" in df.columns else "今天为跌且7天刚好6涨1跌"
            up_col = "等待买点" if "等待买点" in df.columns else ("追涨买点" if "追涨买点" in df.columns else "今天为涨且7天刚好6涨1跌")
            if down_col in df.columns:
                today_down = df[down_col].apply(to_bool).sum()
            if up_col in df.columns:
                today_up = df[up_col].apply(to_bool).sum()
            
            results[combo_name] = {
                "desc": combo_desc,
                "combo_type": combo_type,
                "count": count,
                "today_down": today_down,
                "today_up": today_up,
                "file": latest.name,
                "df": df
            }
            all_stocks[combo_name] = set(df["代码"].tolist()) if "代码" in df.columns else set()
        else:
            results[combo_name] = {
                "desc": combo_desc,
                "combo_type": combo_type,
                "count": 0,
                "today_down": 0,
                "today_up": 0,
                "file": "未找到",
                "df": pd.DataFrame()
            }
            all_stocks[combo_name] = set()
    
    print("\n[UP] 各组合筛选结果统计:")
    print("-" * 70)
    print(f"{'组合':<18} {'数量':>6} {'买入[STAR]':>10} {'等待[STAR]':>10} {'组合类型':>10}")
    print("-" * 70)
    
    for combo_name, data in results.items():
        count = data['count']
        down = data['today_down']
        up = data['today_up']
        combo_type = data['combo_type']
        print(f"  {combo_name:<16} {count:>6}只 {down:>10}只 {up:>10}只 {combo_type:>10}")
    
    print("\n[CHART] 按组合类型汇总:")
    print("-" * 70)
    
    combo_types = {}
    for combo_name, data in results.items():
        ct = data['combo_type']
        if ct not in combo_types:
            combo_types[ct] = {"count": 0, "down": 0, "up": 0}
        combo_types[ct]["count"] += data["count"]
        combo_types[ct]["down"] += data["today_down"]
        combo_types[ct]["up"] += data["today_up"]
    
    type_desc = {
        "134": "完整组合 (稳步上升+趋势+网格)",
        "13": "稳步上升+趋势",
        "34": "趋势+网格",
        "14": "稳步上升+网格",
        "1": "仅稳步上升",
        "4": "仅网格",
    }
    
    for ct in ["134", "13", "34", "14", "1", "4"]:
        if ct in combo_types:
            data = combo_types[ct]
            desc = type_desc.get(ct, ct)
            print(f"  {ct:<5} {desc:<30} 总计: {data['count']:>4}只 (买入[STAR]:{data['down']}只, 等待[STAR]:{data['up']}只)")
    
    print("\n🔍 命中率分析:")
    print("-" * 70)
    
    set_134_61 = all_stocks.get("xuanxue_134_61", set())
    set_34_61 = all_stocks.get("xuanxue_34_61", set())
    set_14_61 = all_stocks.get("xuanxue_14_61", set())
    set_13_61 = all_stocks.get("xuanxue_13_61", set())
    set_1_61 = all_stocks.get("xuanxue_1_61", set())
    set_4_61 = all_stocks.get("xuanxue_4_61", set())
    
    if set_34_61:
        hit_rate = len(set_134_61) / len(set_34_61) * 100 if set_34_61 else 0
        print(f"  稳步上升筛选效果 (134_61 vs 34_61): {len(set_134_61)}/{len(set_34_61)} = {hit_rate:.1f}%")
    if set_14_61:
        hit_rate = len(set_134_61) / len(set_14_61) * 100 if set_14_61 else 0
        print(f"  趋势分析筛选效果 (134_61 vs 14_61): {len(set_134_61)}/{len(set_14_61)} = {hit_rate:.1f}%")
    if set_13_61:
        hit_rate = len(set_134_61) / len(set_13_61) * 100 if set_13_61 else 0
        print(f"  网格筛选效果 (134_61 vs 13_61): {len(set_134_61)}/{len(set_13_61)} = {hit_rate:.1f}%")
    
    print(f"\n  单条件筛选对比:")
    print(f"    仅稳步上升(1): {len(set_1_61)}只")
    print(f"    仅网格(4): {len(set_4_61)}只")
    if set_1_61 and set_4_61:
        common = set_1_61 & set_4_61
        print(f"    两者交集: {len(common)}只")
    
    return results, all_stocks


def generate_recommendations(results: dict, all_stocks: dict):
    """生成股票推荐（带优先级）"""
    print("\n" + "=" * 70)
    print("🎯 股票推荐（基于组合分析）")
    print("=" * 70)
    print("\n优先级说明: [STAR]买入（6连阳后阴线，立即买入）> [STAR]等待（第6天阳线，等明天回调再买）> 无标记")
    
    rec_df = results.get("xuanxue_134_61", {}).get("df", pd.DataFrame())
    if not rec_df.empty and "代码" in rec_df.columns:
        print("\n[STAR][STAR][STAR] 强烈推荐 (134_61 - 全条件满足):")
        print("-" * 70)
        for _, row in rec_df.iterrows():
            code = row.get("代码", "")
            name = row.get("名称", "")
            price = row.get("最新价", "")
            industry = row.get("行业", "")
            priority = get_priority_label(row)
            print(f"  {priority:<10} {code} {name:<10} ￥{price:<8} {industry}")
        print(f"\n  总计: {len(rec_df)} 只")
    
    rec_df_14 = results.get("xuanxue_14_61", {}).get("df", pd.DataFrame())
    set_134_61 = all_stocks.get("xuanxue_134_61", set())
    if not rec_df_14.empty and "代码" in rec_df_14.columns:
        filtered = rec_df_14[~rec_df_14["代码"].isin(set_134_61)]
        if not filtered.empty:
            print("\n[STAR][STAR] 推荐 (14_61 - 稳步上升+网格):")
            print("-" * 70)
            for _, row in filtered.iterrows():
                code = row.get("代码", "")
                name = row.get("名称", "")
                price = row.get("最新价", "")
                industry = row.get("行业", "")
                priority = get_priority_label(row)
                print(f"  {priority:<10} {code} {name:<10} ￥{price:<8} {industry}")
            print(f"\n  总计: {len(filtered)} 只")
    
    rec_df_13 = results.get("xuanxue_13_61", {}).get("df", pd.DataFrame())
    set_14_61 = all_stocks.get("xuanxue_14_61", set())
    already_shown = set_134_61 | set_14_61
    if not rec_df_13.empty and "代码" in rec_df_13.columns:
        filtered = rec_df_13[~rec_df_13["代码"].isin(already_shown)]
        if not filtered.empty:
            print("\n[STAR] 观察 (13_61 - 稳步上升+趋势):")
            print("-" * 70)
            for _, row in filtered.head(15).iterrows():
                code = row.get("代码", "")
                name = row.get("名称", "")
                price = row.get("最新价", "")
                industry = row.get("行业", "")
                priority = get_priority_label(row)
                print(f"  {priority:<10} {code} {name:<10} ￥{price:<8} {industry}")
            if len(filtered) > 15:
                print(f"    ... 还有 {len(filtered) - 15} 只")
            print(f"\n  总计: {len(filtered)} 只")


def save_recommendation_report(results: dict, all_stocks: dict):
    """保存推荐报告"""
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    batch_date = now.strftime("%Y-%m-%d")
    batch_time = now.strftime("%H-%M-%S")
    batch_dir = OUTPUT_DIR / batch_date / batch_time
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = batch_dir / f"recommendation_report_{ts}.md"
    
    lines = [
        f"# 股票推荐报告 ({ts})",
        "",
        "## 优先级说明",
        "",
        "- [STAR] **买入**: 6连阳后阴线（最佳买入时机，立即买入）",
        "- [STAR] **等待**: 第6天阳线（等明天回调再买）",
        "- 无标记: 满足玄学条件但不满足以上特定时点",
        "",
        "## 玄学条件说明",
        "",
        "- 6连阳: 连续6天收阳线（收盘价 > 开盘价）",
        "- 买入信号: 6连阳后第7天收阴线，是回调进场的好时机",
        "- 等待信号: 正在形成第6天阳线，等明天回调再买",
        "",
        "## 组合筛选统计",
        "",
        "| 组合 | 描述 | 数量 | 买入[STAR] | 等待[STAR] |",
        "|------|------|------|--------|--------|",
    ]
    
    combos = {
        "xuanxue_134_61": "玄学61 + 稳步上升 + 趋势 + 网格",
        "xuanxue_134_6": "玄学6 + 稳步上升 + 趋势 + 网格",
        "xuanxue_13_61": "玄学61 + 稳步上升 + 趋势",
        "xuanxue_13_6": "玄学6 + 稳步上升 + 趋势",
        "xuanxue_34_61": "玄学61 + 趋势 + 网格",
        "xuanxue_34_6": "玄学6 + 趋势 + 网格",
        "xuanxue_14_61": "玄学61 + 稳步上升 + 网格",
        "xuanxue_14_6": "玄学6 + 稳步上升 + 网格",
        "xuanxue_1_61": "玄学61 + 稳步上升",
        "xuanxue_1_6": "玄学6 + 稳步上升",
        "xuanxue_4_61": "玄学61 + 网格",
        "xuanxue_4_6": "玄学6 + 网格",
    }
    
    for combo_name, combo_desc in combos.items():
        data = results.get(combo_name, {})
        count = data.get("count", 0)
        down = data.get("today_down", 0)
        up = data.get("today_up", 0)
        lines.append(f"| {combo_name} | {combo_desc} | {count} | {down} | {up} |")
    
    lines += ["", "## 命中率分析", ""]
    
    set_134_61 = all_stocks.get("xuanxue_134_61", set())
    set_34_61 = all_stocks.get("xuanxue_34_61", set())
    set_14_61 = all_stocks.get("xuanxue_14_61", set())
    set_13_61 = all_stocks.get("xuanxue_13_61", set())
    set_1_61 = all_stocks.get("xuanxue_1_61", set())
    set_4_61 = all_stocks.get("xuanxue_4_61", set())
    
    if set_34_61:
        hit_rate = len(set_134_61) / len(set_34_61) * 100
        lines.append(f"- 稳步上升筛选 (134_61/34_61): {len(set_134_61)}/{len(set_34_61)} = **{hit_rate:.1f}%**")
    if set_14_61:
        hit_rate = len(set_134_61) / len(set_14_61) * 100
        lines.append(f"- 趋势分析筛选 (134_61/14_61): {len(set_134_61)}/{len(set_14_61)} = **{hit_rate:.1f}%**")
    if set_13_61:
        hit_rate = len(set_134_61) / len(set_13_61) * 100
        lines.append(f"- 网格筛选 (134_61/13_61): {len(set_134_61)}/{len(set_13_61)} = **{hit_rate:.1f}%**")
    
    lines += ["", f"- 仅稳步上升(1): {len(set_1_61)}只", f"- 仅网格(4): {len(set_4_61)}只", f"- 两者交集: {len(set_1_61 & set_4_61)}只"]
    
    # 推荐列表
    lines += ["", "## [STAR][STAR][STAR] 强烈推荐 (134_61)", "", "满足全部条件：玄学近10天6涨1跌 + 稳步上升 + 趋势信号 + 网格突破", ""]
    
    rec_df = results.get("xuanxue_134_61", {}).get("df", pd.DataFrame())
    if not rec_df.empty and "代码" in rec_df.columns:
        lines.append("| 优先级 | 代码 | 名称 | 最新价 | 行业 |")
        lines.append("|--------|------|------|--------|------|")
        for _, row in rec_df.iterrows():
            priority = get_priority_label(row)
            lines.append(f"| {priority} | {row.get('代码', '')} | {row.get('名称', '')} | {row.get('最新价', '')} | {row.get('行业', '')} |")
    else:
        lines.append("无符合条件的股票")
    
    # 14_61
    lines += ["", "## [STAR][STAR] 推荐 (14_61)", "", "满足条件：玄学近10天6涨1跌 + 稳步上升 + 网格突破", ""]
    rec_df_14 = results.get("xuanxue_14_61", {}).get("df", pd.DataFrame())
    if not rec_df_14.empty and "代码" in rec_df_14.columns:
        filtered = rec_df_14[~rec_df_14["代码"].isin(set_134_61)]
        if not filtered.empty:
            lines.append("| 优先级 | 代码 | 名称 | 最新价 | 行业 |")
            lines.append("|--------|------|------|--------|------|")
            for _, row in filtered.iterrows():
                priority = get_priority_label(row)
                lines.append(f"| {priority} | {row.get('代码', '')} | {row.get('名称', '')} | {row.get('最新价', '')} | {row.get('行业', '')} |")
        else:
            lines.append("所有股票已在强烈推荐中")
    else:
        lines.append("无符合条件的股票")
    
    # 13_61
    lines += ["", "## [STAR] 观察 (13_61)", "", "满足条件：玄学近10天6涨1跌 + 稳步上升 + 趋势信号", ""]
    rec_df_13 = results.get("xuanxue_13_61", {}).get("df", pd.DataFrame())
    already_shown = set_134_61 | set_14_61
    if not rec_df_13.empty and "代码" in rec_df_13.columns:
        filtered = rec_df_13[~rec_df_13["代码"].isin(already_shown)]
        if not filtered.empty:
            lines.append("| 优先级 | 代码 | 名称 | 最新价 | 行业 |")
            lines.append("|--------|------|------|--------|------|")
            for _, row in filtered.iterrows():
                priority = get_priority_label(row)
                lines.append(f"| {priority} | {row.get('代码', '')} | {row.get('名称', '')} | {row.get('最新价', '')} | {row.get('行业', '')} |")
        else:
            lines.append("所有股票已在推荐列表中")
    else:
        lines.append("无符合条件的股票")
    
    # 1_61
    lines += ["", "## 📋 备选 (1_61)", "", "满足条件：玄学近10天6涨1跌 + 稳步上升", ""]
    rec_df_1 = results.get("xuanxue_1_61", {}).get("df", pd.DataFrame())
    already_shown = already_shown | set_13_61
    if not rec_df_1.empty and "代码" in rec_df_1.columns:
        filtered = rec_df_1[~rec_df_1["代码"].isin(already_shown)]
        if not filtered.empty:
            lines.append("| 优先级 | 代码 | 名称 | 最新价 | 行业 |")
            lines.append("|--------|------|------|--------|------|")
            for _, row in filtered.iterrows():
                priority = get_priority_label(row)
                lines.append(f"| {priority} | {row.get('代码', '')} | {row.get('名称', '')} | {row.get('最新价', '')} | {row.get('行业', '')} |")
        else:
            lines.append("所有股票已在推荐列表中")
    else:
        lines.append("无符合条件的股票")
    
    lines += ["", "---", "", f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"]
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"\n📝 报告已保存: {report_path}")
    return report_path


def main():
    results, all_stocks = analyze_combinations()
    generate_recommendations(results, all_stocks)
    report_path = save_recommendation_report(results, all_stocks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
