# -*- coding: utf-8 -*-
"""
玄学联合筛选（xuanxue6/xuanxue61 + 1/3/4）

依赖：
- trend_rules_detail_*.csv（玄学条件 + 趋势规则信号）
- steady_uptrend_*.csv（稳步上升扫描结果）
- vol_contraction_grid_summary_*.csv（网格测试最优参数，用于 4 的判定）

输出：
- output/YYYY-MM-DD/HH-MM-SS/xuanxue_XXX_*.csv
- output/YYYY-MM-DD/HH-MM-SS/xuanxue_XXX_*.md

玄学条件说明：
- 6up1down: 10天窗口内有连续6阳后1阴模式
- 6up: 最近6天连续阳线
- 回调优先: 今天阴线且前6天6连阳（最佳买入机会）
- 追涨优先: 今天是第6天阳线（顺势追涨）
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from pandas.errors import EmptyDataError

from data_loader import load_daily_data
from grid_test_vol_contraction import bollinger_bands, volume_ratio
from mystic_indicators import MYSTIC_COLUMN_MAP, get_mystic_priority


@dataclass
class GridCombo:
    bb_window: int
    num_std: float
    quantile: float
    quantile_window: int
    vol_ratio_threshold: float
    horizon: int


def to_bool(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y", "是"}


def find_latest(output_dir: Path, pattern: str) -> Optional[Path]:
    """递归搜索最新的匹配文件，包括批次文件夹"""
    # 先在根目录搜索（兼容旧文件）
    files = sorted(output_dir.glob(pattern), reverse=True)
    
    # 递归搜索批次文件夹中的文件
    batch_files = sorted(output_dir.glob(f"*/*/{pattern}"), reverse=True)
    
    # 合并并按路径（包含时间戳）排序
    all_files = files + batch_files
    return all_files[0] if all_files else None


def read_csv_utf8(path: Path) -> pd.DataFrame:
    def _normalize_cols(frame: pd.DataFrame) -> pd.DataFrame:
        rename_map = {}
        for col in frame.columns:
            text = (
                str(col)
                .replace("\ufeff", "")
                .replace("\u200b", "")
                .replace("\u200e", "")
                .replace("\u200f", "")
                .strip()
            )
            rename_map[col] = text
        return frame.rename(columns=rename_map)

    df = pd.read_csv(path, encoding="utf-8-sig")
    df = _normalize_cols(df)
    if "代码" not in df.columns and any("�" in str(c) for c in df.columns):
        df = pd.read_csv(path, encoding="gbk")
        df = _normalize_cols(df)
    return df


def load_best_grid_combo(summary_path: Path, horizon: int) -> Optional[GridCombo]:
    df = read_csv_utf8(summary_path)
    df = df[df["horizon"] == horizon].copy()
    if df.empty:
        return None
    df = df[df["avg_return"].notna()].copy()
    if df.empty:
        return None
    df = df.sort_values(by=["avg_return", "count"], ascending=[False, False])
    row = df.iloc[0]
    return GridCombo(
        bb_window=int(row["bb_window"]),
        num_std=float(row["num_std"]),
        quantile=float(row["quantile"]),
        quantile_window=int(row["quantile_window"]),
        vol_ratio_threshold=float(row["vol_ratio_threshold"]),
        horizon=int(row["horizon"]),
    )


def has_vol_contraction_signal(code: str, combo: GridCombo, lookback_days: int, min_bars: int) -> bool:
    try:
        df = load_daily_data(code)
        if df.empty or len(df) < min_bars:
            return False

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).reset_index(drop=True)
        if df.empty or len(df) < min_bars:
            return False

        close = df["close"].astype(float)
        vols = df["volume"].astype(float)

        bb = bollinger_bands(close, combo.bb_window, combo.num_std)
        bandwidth = bb["bandwidth"]
        vol_ratio = volume_ratio(vols, 20)

        low_vol = bandwidth <= bandwidth.rolling(combo.quantile_window).quantile(combo.quantile)
        breakout = close > bb["upper"]
        vol_confirm = vol_ratio >= combo.vol_ratio_threshold

        signal = low_vol & breakout & vol_confirm
        if not signal.any():
            return False

        last_date = df["date"].iloc[-1]
        cutoff = last_date - pd.Timedelta(days=lookback_days)
        recent = df[signal & (df["date"] >= cutoff)]
        return not recent.empty
    except Exception:
        return False


def get_code_series(df: pd.DataFrame) -> tuple[pd.Series, str] | tuple[None, None]:
    def _norm(text: str) -> str:
        return (
            text.replace("\ufeff", "")
            .replace("\u200b", "")
            .replace("\u200e", "")
            .replace("\u200f", "")
            .strip()
        )

    for col in df.columns:
        text = _norm(str(col))
        if text in {"代码", "code", "股票代码"}:
            return df[col], col
    for col in df.columns:
        text = _norm(str(col))
        if "代码" in text or "code" in text.lower():
            return df[col], col
    return None, None


def build_candidates(
    trend_df: pd.DataFrame,
    steady_path: Path | None,
    grid_path: Path | None,
    grid_horizon: int,
    lookback: int,
    min_bars: int,
    mode: str,
    include_steady: bool,
    include_trend: bool,
    include_grid: bool,
) -> tuple[pd.DataFrame, GridCombo | None]:
    # 玄学条件筛选（支持新旧列名）
    if mode == "6up1down":
        # 新列名优先，兼容旧列名
        col_name = "玄学_10天内有6连阳后1阴" if "玄学_10天内有6连阳后1阴" in trend_df.columns else "玄学_近10天6涨1跌"
        mystic_mask = trend_df.get(col_name, pd.Series([False] * len(trend_df)))
    else:
        col_name = "玄学_最近6天连续阳线" if "玄学_最近6天连续阳线" in trend_df.columns else "玄学_连续6天阳线"
        mystic_mask = trend_df.get(col_name, pd.Series([False] * len(trend_df)))

    # 趋势条件（可选）
    if include_trend:
        trend_mask = (
            trend_df.get("趋势跟随_是否信号", False)
            | trend_df.get("上升回撤_是否信号", False)
            | trend_df.get("波动收缩突破_是否信号", False)
        )
        candidates = trend_df[mystic_mask & trend_mask].copy()
    else:
        candidates = trend_df[mystic_mask].copy()

    # 添加优先级列（支持新旧列名）
    # 回调优先：今天阴线且前6天6连阳
    callback_col = "玄学_今天阴线且前6天连阳(回调)" if "玄学_今天阴线且前6天连阳(回调)" in trend_df.columns else "玄学_今天为跌且7天刚好6涨1跌"
    if callback_col in trend_df.columns:
        candidates["回调买点"] = trend_df.loc[candidates.index, callback_col].map(to_bool)
    else:
        candidates["回调买点"] = False
    
    # 等待信号：今天是第6天阳线，等明天回调再买
    wait_col = "玄学_今天是第6天阳线(等待)" if "玄学_今天是第6天阳线(等待)" in trend_df.columns else ("玄学_今天是第6天阳线(追涨)" if "玄学_今天是第6天阳线(追涨)" in trend_df.columns else "玄学_今天为涨且7天刚好6涨1跌")
    if wait_col in trend_df.columns:
        candidates["等待买点"] = trend_df.loc[candidates.index, wait_col].map(to_bool)
    else:
        candidates["等待买点"] = False

    code_series, code_col = get_code_series(candidates)
    if code_series is None or code_col is None:
        # 空DataFrame时直接返回
        if candidates.empty:
            return candidates, None
        raise ValueError(f"找不到代码列，当前列: {list(candidates.columns)}")

    best_combo: GridCombo | None = None

    if include_steady:
        if steady_path is None or not steady_path.exists():
            raise FileNotFoundError("找不到 steady_uptrend_*.csv，请先运行 scan_steady_uptrend.py")
        try:
            steady_df = read_csv_utf8(steady_path)
        except EmptyDataError:
            steady_df = pd.DataFrame(columns=["code", "steady_uptrend"])
        if "code" not in steady_df.columns or "steady_uptrend" not in steady_df.columns:
            raise ValueError("steady_uptrend 文件缺少 code/steady_uptrend 列")
        steady_df["steady_uptrend"] = steady_df["steady_uptrend"].map(to_bool)
        steady_map = dict(zip(steady_df["code"].astype(str), steady_df["steady_uptrend"]))
        candidates["稳步上升_是否信号"] = code_series.astype(str).map(lambda c: bool(steady_map.get(c, False)))
        candidates = candidates[candidates["稳步上升_是否信号"]]
        # 重新获取 code_series（过滤后索引已变）
        code_series, code_col = get_code_series(candidates)

    if include_grid:
        if grid_path is None or not grid_path.exists():
            raise FileNotFoundError("找不到 vol_contraction_grid_summary_*.csv，请先运行 grid_test_vol_contraction.py")
        best_combo = load_best_grid_combo(grid_path, grid_horizon)
        if not best_combo:
            raise ValueError("网格汇总中未找到可用的最优参数")
        if code_series is not None and not candidates.empty:
            candidates["网格突破_是否信号"] = code_series.astype(str).map(
                lambda c: has_vol_contraction_signal(c, best_combo, lookback, min_bars)
            )
            candidates = candidates[candidates["网格突破_是否信号"]]

    # 优先级排序：回调优先 > 等待 > 其他
    sort_cols = []
    if "回调买点" in candidates.columns:
        sort_cols.append("回调买点")
    if "等待买点" in candidates.columns:
        sort_cols.append("等待买点")
    if sort_cols:
        candidates = candidates.sort_values(by=sort_cols, ascending=False)

    return candidates, best_combo


def write_report(
    report_path: Path,
    candidates: pd.DataFrame,
    trend_path: Path,
    steady_path: Path | None,
    grid_path: Path | None,
    best_combo: GridCombo | None,
    grid_horizon: int,
    strategy_name: str,
    mode_label: str,
    combo_label: str,
) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_lines = [
        f"# 玄学联合筛选（{strategy_name}）报告 ({ts})",
        "",
        f"- 策略: {strategy_name}",
        f"- 玄学条件: {mode_label}",
        f"- 组合条件: {combo_label}",
        f"- 来源明细: {trend_path.name}",
        f"- 稳步上升: {steady_path.name if steady_path else '未使用'}",
        f"- 网格参数: {grid_path.name if grid_path else '未使用'}",
        f"- 网格收益周期: {grid_horizon}",
        f"- 候选数量: {len(candidates)}",
    ]

    if best_combo:
        report_lines += [
            "",
            "## 网格最优参数",
            "",
            f"- bb_window: {best_combo.bb_window}",
            f"- num_std: {best_combo.num_std}",
            f"- quantile: {best_combo.quantile}",
            f"- quantile_window: {best_combo.quantile_window}",
            f"- vol_ratio_threshold: {best_combo.vol_ratio_threshold}",
        ]

    report_lines += [
        "",
        "## 股票明细",
        "",
        "优先级说明: [STAR]买入（6连阳后阴线，立即买入）> [STAR]等待（第6天阳线，等明天回调再买）> 无标记",
        "",
    ]
    if candidates.empty:
        report_lines.append("无命中样本")
    else:
        display_cols = ["代码", "名称", "板块", "行业", "最新日期", "最新价", "回调买点", "等待买点"]
        existing_cols = [c for c in display_cols if c in candidates.columns]
        if existing_cols:
            show_df = candidates[existing_cols].copy()
            # 添加优先级标记列
            def get_priority(row):
                if row.get("回调买点", False) in [True, "True", "true", 1, "1"]:
                    return "[STAR]买入"
                if row.get("等待买点", False) in [True, "True", "true", 1, "1"]:
                    return "[STAR]等待"
                return ""
            show_df.insert(0, "优先级", show_df.apply(get_priority, axis=1))
            # 移除原始布尔列，只保留优先级
            for col in ["回调买点", "等待买点"]:
                if col in show_df.columns:
                    show_df = show_df.drop(columns=[col])
            report_lines.append(show_df.to_markdown(index=False))
        else:
            report_lines.append("无可展示字段")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))


def migrate_legacy_outputs(output_dir: Path) -> int:
    legacy_candidates = sorted(output_dir.glob("xuanxue134_candidates_*.csv"))
    legacy_reports = sorted(output_dir.glob("xuanxue134_report_*.md"))

    if not legacy_candidates and not legacy_reports:
        print("[INFO] 未找到旧版 xuanxue134 输出，无需迁移")
        return 0

    counts_by_ts: dict[str, tuple[int, int]] = {}
    for path in legacy_candidates:
        ts = path.stem.replace("xuanxue134_candidates_", "")
        df = read_csv_utf8(path)
        df["玄学_近10天6涨1跌"] = df.get("玄学_近10天6涨1跌", False).map(to_bool)
        df["玄学_连续6天阳线"] = df.get("玄学_连续6天阳线", False).map(to_bool)

        df_6 = df[df["玄学_连续6天阳线"] == True].copy()
        df_61 = df[df["玄学_近10天6涨1跌"] == True].copy()

        count_6 = len(df_6)
        count_61 = len(df_61)
        counts_by_ts[ts] = (count_6, count_61)
        out_6 = output_dir / f"xuanxue_134_6_{count_6}只_{ts}.csv"
        out_61 = output_dir / f"xuanxue_134_61_{count_61}只_{ts}.csv"
        df_6.to_csv(out_6, index=False, encoding="utf-8-sig")
        df_61.to_csv(out_61, index=False, encoding="utf-8-sig")
        print(f"[OK] 迁移CSV：{out_6}")
        print(f"[OK] 迁移CSV：{out_61}")

    for path in legacy_reports:
        ts = path.stem.replace("xuanxue134_report_", "")
        content = path.read_text(encoding="utf-8")

        count_6, count_61 = counts_by_ts.get(ts, (0, 0))
        for strategy_name, mode_label, count_label in [
            ("xuanxue_134_6", "玄学条件2（连续6天阳线）", f"{count_6}只"),
            ("xuanxue_134_61", "玄学条件1（近10天6涨1跌）", f"{count_61}只"),
        ]:
            new_path = output_dir / f"{strategy_name}_{count_label}_{ts}.md"
            header = [
                f"# 玄学联合筛选（{strategy_name}）报告 ({ts})",
                "",
                f"- 策略: {strategy_name}",
                f"- 玄学条件: {mode_label}",
                "- 组合条件: 1(稳步上升) + 3(多规则趋势分析) + 4(网格测试)",
                "- 说明: 由旧版合并报告拆分生成，详情见下文",
                "",
            ]
            new_path.write_text("\n".join(header) + content, encoding="utf-8")
            print(f"[OK] 迁移报告：{new_path}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="玄学联合筛选（xuanxue6/xuanxue61 + 1/3/4）")
    parser.add_argument("--trend-detail", type=str, default=None, help="trend_rules_detail_*.csv 路径")
    parser.add_argument("--steady-uptrend", type=str, default=None, help="steady_uptrend_*.csv 路径")
    parser.add_argument("--grid-summary", type=str, default=None, help="vol_contraction_grid_summary_*.csv 路径")
    parser.add_argument("--grid-horizon", type=int, default=20, help="网格测试选择的收益周期")
    parser.add_argument("--lookback", type=int, default=120, help="网格信号回看天数")
    parser.add_argument("--min-bars", type=int, default=120, help="最少K线数量")
    parser.add_argument("--output", type=str, default=None, help="输出CSV路径")
    parser.add_argument("--migrate", action="store_true", help="迁移旧版 xuanxue134 输出为新命名")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.migrate:
        return migrate_legacy_outputs(output_dir)

    trend_path = Path(args.trend_detail) if args.trend_detail else find_latest(output_dir, "trend_rules_detail_*.csv")
    if trend_path is None or not trend_path.exists():
        raise FileNotFoundError("找不到 trend_rules_detail_*.csv，请先运行 trend_rules_analyzer.py")

    steady_path = Path(args.steady_uptrend) if args.steady_uptrend else find_latest(output_dir, "steady_uptrend_*.csv")
    grid_path = Path(args.grid_summary) if args.grid_summary else find_latest(output_dir, "vol_contraction_grid_summary_*.csv")

    trend_df = read_csv_utf8(trend_path)
    
    # 玄学条件列名映射（支持新旧列名）
    # 新列名: 玄学_10天内有6连阳后1阴, 玄学_最近6天连续阳线, ...
    # 旧列名: 玄学_近10天6涨1跌, 玄学_连续6天阳线, ...
    mystic_col_aliases = {
        "玄学_10天内有6连阳后1阴": ["玄学_10天内有6连阳后1阴", "玄学_近10天6涨1跌"],
        "玄学_最近6天连续阳线": ["玄学_最近6天连续阳线", "玄学_连续6天阳线"],
        "玄学_今天阴线且前6天连阳(回调)": ["玄学_今天阴线且前6天连阳(回调)", "玄学_今天为跌且7天刚好6涨1跌"],
        "玄学_今天是第6天阳线(追涨)": ["玄学_今天是第6天阳线(追涨)", "玄学_今天为涨且7天刚好6涨1跌"],
    }
    
    # 统一列名（兼容新旧格式）
    for standard_name, aliases in mystic_col_aliases.items():
        for alias in aliases:
            if alias in trend_df.columns and standard_name not in trend_df.columns:
                trend_df[standard_name] = trend_df[alias].map(to_bool)
                break
        if standard_name in trend_df.columns:
            trend_df[standard_name] = trend_df[standard_name].map(to_bool)
    
    # 趋势信号布尔转换
    for col in ["趋势跟随_是否信号", "上升回撤_是否信号", "波动收缩突破_是否信号"]:
        if col in trend_df.columns:
            trend_df[col] = trend_df[col].map(to_bool)

    # 生成时间戳和批次文件夹
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    batch_date = now.strftime("%Y-%m-%d")
    batch_time = now.strftime("%H-%M-%S")
    batch_dir = output_dir / batch_date / batch_time
    batch_dir.mkdir(parents=True, exist_ok=True)
    base_label = "baseon_unknown"
    if "最新日期" in trend_df.columns:
        base_date = pd.to_datetime(trend_df["最新日期"], errors="coerce").max()
        if pd.notna(base_date):
            base_label = f"baseon_{base_date.strftime('%m%d%Y')}"

    # 扩展组合：
    # 1 = 稳步上升
    # 3 = 多规则趋势分析
    # 4 = 网格测试
    # 组合：134, 13, 34, 14, 1, 4
    outputs = [
        # 完整组合 134
        ("6up", "xuanxue_134_6", "玄学条件2（连续6天阳线）", True, True, True, "1(稳步上升) + 3(趋势分析) + 4(网格测试)"),
        ("6up1down", "xuanxue_134_61", "玄学条件1（近10天6涨1跌）", True, True, True, "1(稳步上升) + 3(趋势分析) + 4(网格测试)"),
        # 组合 13
        ("6up", "xuanxue_13_6", "玄学条件2（连续6天阳线）", True, True, False, "1(稳步上升) + 3(趋势分析)"),
        ("6up1down", "xuanxue_13_61", "玄学条件1（近10天6涨1跌）", True, True, False, "1(稳步上升) + 3(趋势分析)"),
        # 组合 34
        ("6up", "xuanxue_34_6", "玄学条件2（连续6天阳线）", False, True, True, "3(趋势分析) + 4(网格测试)"),
        ("6up1down", "xuanxue_34_61", "玄学条件1（近10天6涨1跌）", False, True, True, "3(趋势分析) + 4(网格测试)"),
        # 组合 14
        ("6up", "xuanxue_14_6", "玄学条件2（连续6天阳线）", True, False, True, "1(稳步上升) + 4(网格测试)"),
        ("6up1down", "xuanxue_14_61", "玄学条件1（近10天6涨1跌）", True, False, True, "1(稳步上升) + 4(网格测试)"),
        # 仅组合 1
        ("6up", "xuanxue_1_6", "玄学条件2（连续6天阳线）", True, False, False, "1(稳步上升)"),
        ("6up1down", "xuanxue_1_61", "玄学条件1（近10天6涨1跌）", True, False, False, "1(稳步上升)"),
        # 仅组合 4
        ("6up", "xuanxue_4_6", "玄学条件2（连续6天阳线）", False, False, True, "4(网格测试)"),
        ("6up1down", "xuanxue_4_61", "玄学条件1（近10天6涨1跌）", False, False, True, "4(网格测试)"),
    ]

    out_cols = [
        "代码",
        "名称",
        "板块",
        "行业",
        "最新日期",
        "最新价",
        "玄学_近10天6涨1跌",
        "玄学_连续6天阳线",
        "回调买点",
        "等待买点",
        "趋势跟随_是否信号",
        "上升回撤_是否信号",
        "波动收缩突破_是否信号",
        "稳步上升_是否信号",
        "网格突破_是否信号",
    ]

    for mode, strategy_name, mode_label, use_steady, use_trend, use_grid, combo_label in outputs:
        candidates, best_combo = build_candidates(
            trend_df=trend_df,
            steady_path=steady_path,
            grid_path=grid_path,
            grid_horizon=args.grid_horizon,
            lookback=args.lookback,
            min_bars=args.min_bars,
            mode=mode,
            include_steady=use_steady,
            include_trend=use_trend,
            include_grid=use_grid,
        )

        count_label = f"{len(candidates)}只"
        output_path = (
            Path(args.output)
            if args.output and mode == "6up"
            else batch_dir / f"{strategy_name}_{count_label}_{base_label}_{ts}.csv"
        )
        report_path = batch_dir / f"{strategy_name}_{count_label}_{base_label}_{ts}.md"

        existing_cols = [c for c in out_cols if c in candidates.columns]
        candidates[existing_cols].to_csv(output_path, index=False, encoding="utf-8-sig")

        write_report(
            report_path=report_path,
            candidates=candidates,
            trend_path=trend_path,
            steady_path=steady_path,
            grid_path=grid_path,
            best_combo=best_combo,
            grid_horizon=args.grid_horizon,
            strategy_name=strategy_name,
            mode_label=mode_label,
            combo_label=combo_label,
        )

        print(f"[OK] 输出完成: {output_path}")
        print(f"[OK] 报告输出: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
