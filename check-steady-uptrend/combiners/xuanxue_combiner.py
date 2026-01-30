# -*- coding: utf-8 -*-
"""
玄学联合组合器

将各分析结果按不同组合条件筛选：
- 134: 稳步上升 + 趋势分析 + 网格测试
- 13: 稳步上升 + 趋势分析
- 34: 趋势分析 + 网格测试
- 14: 稳步上升 + 网格测试
- 1: 仅稳步上升
- 4: 仅网格测试

每种组合同时支持两种玄学条件：
- 6: 连续6天阳线
- 61: 近10天6涨1跌
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd

from data_loader import load_daily_data
from grid_test_vol_contraction import bollinger_bands, volume_ratio
from utils import to_bool


@dataclass
class GridCombo:
    """网格最优参数组合"""
    bb_window: int
    num_std: float
    quantile: float
    quantile_window: int
    vol_ratio_threshold: float
    horizon: int


class XuanxueCombiner:
    """玄学联合组合器"""
    
    # 组合配置：(mode, strategy_name, mode_label, use_steady, use_trend, use_grid, combo_label)
    COMBINATIONS = [
        # 完整组合 134
        ("6up", "xuanxue_134_6", "玄学条件2（连续6天阳线）", True, True, True, "1(稳步上升) + 3(趋势分析) + 4(网格测试)"),
        ("6up1down", "xuanxue_134_61", "玄学条件1（近10天6涨1跌）", True, True, True, "1(稳步上升) + 3(趋势分析) + 4(网格测试)"),
        # 组合 13
        ("6up", "xuanxue_13_6", "玄学条件2（连续6天阳线）", True, True, False, "1(稳步上升) + 3(趋势分析)"),
        ("6up1down", "xuanxue_13_61", "玄学条件1（近10天6涨1跌）", True, True, False, "1(稳步上升) + 3(趋势分析)"),
        # 组合 3（仅趋势分析）
        ("6up", "xuanxue_3_6", "玄学条件2（连续6天阳线）", False, True, False, "3(趋势分析)"),
        ("6up1down", "xuanxue_3_61", "玄学条件1（近10天6涨1跌）", False, True, False, "3(趋势分析)"),
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
    
    def __init__(
        self,
        trend_result: Any,  # AnalysisResult
        steady_result: Optional[Any],
        grid_result: Optional[Any],
        config: Any,  # PipelineConfig
        output_dir: Path
    ):
        self.trend_result = trend_result
        self.steady_result = steady_result
        self.grid_result = grid_result
        self.config = config
        self.output_dir = output_dir
        
        # 准备数据
        self.trend_df = self._prepare_trend_df()
        self.steady_map = self._prepare_steady_map()
        self.best_combo = self._load_best_grid_combo()
    
    def run(self) -> Dict[str, pd.DataFrame]:
        """运行所有组合筛选"""
        results = {}
        
        now = datetime.now()
        ts = now.strftime("%Y%m%d_%H%M%S")
        base_label = self._get_base_label()
        
        for mode, strategy_name, mode_label, use_steady, use_trend, use_grid, combo_label in self.COMBINATIONS:
            candidates, combo = self._build_candidates(
                mode=mode,
                include_steady=use_steady,
                include_trend=use_trend,
                include_grid=use_grid,
            )
            
            count_label = f"{len(candidates)}只"
            
            # 保存CSV
            csv_path = self.output_dir / f"{strategy_name}_{count_label}_{base_label}_{ts}.csv"
            self._save_csv(candidates, csv_path)
            
            # 保存MD报告
            md_path = self.output_dir / f"{strategy_name}_{count_label}_{base_label}_{ts}.md"
            self._save_report(
                candidates=candidates,
                report_path=md_path,
                strategy_name=strategy_name,
                mode_label=mode_label,
                combo_label=combo_label,
                best_combo=combo,
            )
            
            results[strategy_name] = candidates
            print(f"  [OK] {strategy_name}: {len(candidates)} 只")
        
        return results
    
    def _prepare_trend_df(self) -> pd.DataFrame:
        """准备趋势分析数据"""
        if self.trend_result is None:
            return pd.DataFrame()
        
        df = self.trend_result.data.copy()
        
        # 玄学条件列名映射（支持新旧列名）
        mystic_col_aliases = {
            "玄学_10天内有6连阳后1阴": ["玄学_10天内有6连阳后1阴", "玄学_近10天6涨1跌"],
            "玄学_最近6天连续阳线": ["玄学_最近6天连续阳线", "玄学_连续6天阳线"],
            "玄学_今天阴线且前6天连阳(回调)": ["玄学_今天阴线且前6天连阳(回调)", "玄学_今天为跌且7天刚好6涨1跌"],
            "玄学_今天是第6天阳线(等待)": ["玄学_今天是第6天阳线(等待)", "玄学_今天是第6天阳线(追涨)", "玄学_今天为涨且7天刚好6涨1跌"],
        }
        
        # 统一列名
        for standard_name, aliases in mystic_col_aliases.items():
            for alias in aliases:
                if alias in df.columns and standard_name not in df.columns:
                    df[standard_name] = df[alias].map(to_bool)
                    break
            if standard_name in df.columns:
                df[standard_name] = df[standard_name].map(to_bool)
        
        # 趋势信号布尔转换
        for col in ["趋势跟随_是否信号", "上升回撤_是否信号", "波动收缩突破_是否信号"]:
            if col in df.columns:
                df[col] = df[col].map(to_bool)
        
        return df
    
    def _prepare_steady_map(self) -> Dict[str, bool]:
        """准备稳步上升映射"""
        if self.steady_result is None:
            return {}
        
        df = self.steady_result.data
        if df.empty or "steady_uptrend" not in df.columns:
            return {}
            
        df["steady_uptrend"] = df["steady_uptrend"].map(to_bool)
        return dict(zip(df["code"].astype(str), df["steady_uptrend"]))
    
    def _load_best_grid_combo(self) -> Optional[GridCombo]:
        """加载最优网格参数"""
        if self.grid_result is None:
            return None

        # 获取 DataFrame
        if isinstance(self.grid_result, tuple):
            df = self.grid_result[0]
        elif hasattr(self.grid_result, 'data'):
            df = self.grid_result.data
        else:
            df = self.grid_result

        # 确保是 DataFrame
        if not hasattr(df, 'empty'):
            return None

        df = df[df["horizon"] == self.config.grid_horizon].copy()
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
    
    def _get_code_series(self, df: pd.DataFrame):
        """获取代码列"""
        for col in df.columns:
            text = str(col).strip()
            if text in {"代码", "code", "股票代码"}:
                return df[col], col
        return None, None
    
    def _build_candidates(
        self,
        mode: str,
        include_steady: bool,
        include_trend: bool,
        include_grid: bool,
    ) -> tuple[pd.DataFrame, Optional[GridCombo]]:
        """构建候选股票"""
        trend_df = self.trend_df
        
        # 玄学条件筛选
        if mode == "6up1down":
            col_name = "玄学_10天内有6连阳后1阴" if "玄学_10天内有6连阳后1阴" in trend_df.columns else "玄学_近10天6涨1跌"
            mystic_mask = trend_df.get(col_name, pd.Series([False] * len(trend_df)))
        else:
            col_name = "玄学_最近6天连续阳线" if "玄学_最近6天连续阳线" in trend_df.columns else "玄学_连续6天阳线"
            mystic_mask = trend_df.get(col_name, pd.Series([False] * len(trend_df)))
        
        # 趋势条件
        if include_trend:
            trend_mask = (
                trend_df.get("趋势跟随_是否信号", False)
                | trend_df.get("上升回撤_是否信号", False)
                | trend_df.get("波动收缩突破_是否信号", False)
            )
            candidates = trend_df[mystic_mask & trend_mask].copy()
        else:
            candidates = trend_df[mystic_mask].copy()
        
        # 添加优先级列
        callback_col = "玄学_今天阴线且前6天连阳(回调)" if "玄学_今天阴线且前6天连阳(回调)" in trend_df.columns else "玄学_今天为跌且7天刚好6涨1跌"
        if callback_col in trend_df.columns:
            candidates["回调买点"] = trend_df.loc[candidates.index, callback_col].map(to_bool)
        else:
            candidates["回调买点"] = False
        
        wait_col = "玄学_今天是第6天阳线(等待)" if "玄学_今天是第6天阳线(等待)" in trend_df.columns else ("玄学_今天是第6天阳线(追涨)" if "玄学_今天是第6天阳线(追涨)" in trend_df.columns else "玄学_今天为涨且7天刚好6涨1跌")
        if wait_col in trend_df.columns:
            candidates["等待买点"] = trend_df.loc[candidates.index, wait_col].map(to_bool)
        else:
            candidates["等待买点"] = False
        
        code_series, code_col = self._get_code_series(candidates)
        if code_series is None and not candidates.empty:
            raise ValueError(f"找不到代码列，当前列: {list(candidates.columns)}")
        
        best_combo = self.best_combo
        
        # 稳步上升筛选
        if include_steady:
            if not self.steady_map:
                return pd.DataFrame(), None
            candidates["稳步上升_是否信号"] = code_series.astype(str).map(lambda c: bool(self.steady_map.get(c, False)))
            candidates = candidates[candidates["稳步上升_是否信号"]]
            code_series, code_col = self._get_code_series(candidates)
        
        # 网格筛选
        if include_grid:
            if best_combo is None:
                return pd.DataFrame(), None
            if code_series is not None and not candidates.empty:
                candidates["网格突破_是否信号"] = code_series.astype(str).map(
                    lambda c: self._has_vol_contraction_signal(c, best_combo)
                )
                candidates = candidates[candidates["网格突破_是否信号"]]
        
        # 优先级排序
        sort_cols = []
        if "回调买点" in candidates.columns:
            sort_cols.append("回调买点")
        if "等待买点" in candidates.columns:
            sort_cols.append("等待买点")
        if sort_cols:
            candidates = candidates.sort_values(by=sort_cols, ascending=False)
        
        return candidates, best_combo
    
    def _has_vol_contraction_signal(self, code: str, combo: GridCombo) -> bool:
        """检查是否有波动收缩信号"""
        try:
            df = load_daily_data(code)
            if df.empty or len(df) < self.config.min_bars:
                return False
            
            df = df.copy()
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"]).reset_index(drop=True)
            
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
            cutoff = last_date - pd.Timedelta(days=self.config.lookback_days)
            recent = df[signal & (df["date"] >= cutoff)]
            return not recent.empty
        except Exception:
            return False
    
    def _get_base_label(self) -> str:
        """获取基准日期标签"""
        if self.trend_df.empty:
            return "baseon_unknown"
        if "最新日期" in self.trend_df.columns:
            base_date = pd.to_datetime(self.trend_df["最新日期"], errors="coerce").max()
            if pd.notna(base_date):
                return f"baseon_{base_date.strftime('%m%d%Y')}"
        return "baseon_unknown"
    
    def _save_csv(self, candidates: pd.DataFrame, path: Path):
        """保存CSV"""
        out_cols = [
            "代码", "名称", "板块", "行业", "最新日期", "最新价",
            "玄学_近10天6涨1跌", "玄学_连续6天阳线",
            "回调买点", "等待买点",
            "趋势跟随_是否信号", "上升回撤_是否信号", "波动收缩突破_是否信号",
            "稳步上升_是否信号", "网格突破_是否信号",
        ]
        existing_cols = [c for c in out_cols if c in candidates.columns]
        candidates[existing_cols].to_csv(path, index=False, encoding="utf-8-sig")
    
    def _save_report(
        self,
        candidates: pd.DataFrame,
        report_path: Path,
        strategy_name: str,
        mode_label: str,
        combo_label: str,
        best_combo: Optional[GridCombo],
    ):
        """保存MD报告"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        lines = [
            f"# 玄学联合筛选（{strategy_name}）报告 ({ts})",
            "",
            f"- 策略: {strategy_name}",
            f"- 玄学条件: {mode_label}",
            f"- 组合条件: {combo_label}",
            f"- 候选数量: {len(candidates)}",
        ]
        
        if best_combo:
            lines += [
                "",
                "## 网格最优参数",
                "",
                f"- bb_window: {best_combo.bb_window}",
                f"- num_std: {best_combo.num_std}",
                f"- quantile: {best_combo.quantile}",
                f"- quantile_window: {best_combo.quantile_window}",
                f"- vol_ratio_threshold: {best_combo.vol_ratio_threshold}",
            ]
        
        # 行业/板块统计
        if not candidates.empty:
            lines += self._generate_industry_stats(candidates)
        
        lines += [
            "",
            "## 股票明细",
            "",
            "优先级说明: [STAR]买入（6连阳后阴线，立即买入）> [STAR]等待（第6天阳线，等明天回调再买）> 无标记",
            "",
        ]
        
        if candidates.empty:
            lines.append("无命中样本")
        else:
            display_cols = ["代码", "名称", "板块", "行业", "最新日期", "最新价", "回调买点", "等待买点"]
            existing_cols = [c for c in display_cols if c in candidates.columns]
            
            if existing_cols:
                show_df = candidates[existing_cols].copy()
                
                def get_priority(row):
                    if row.get("回调买点", False) in [True, "True", "true", 1, "1"]:
                        return "[STAR]买入"
                    if row.get("等待买点", False) in [True, "True", "true", 1, "1"]:
                        return "[STAR]等待"
                    return ""
                
                show_df.insert(0, "优先级", show_df.apply(get_priority, axis=1))
                
                for col in ["回调买点", "等待买点"]:
                    if col in show_df.columns:
                        show_df = show_df.drop(columns=[col])
                
                lines.append(show_df.to_markdown(index=False))
            else:
                lines.append("无可展示字段")
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    
    def _generate_industry_stats(self, candidates: pd.DataFrame) -> List[str]:
        """生成行业/板块统计"""
        lines = []
        total = len(candidates)
        
        # 板块统计
        if "板块" in candidates.columns:
            board_counts = candidates["板块"].value_counts().reset_index()
            board_counts.columns = ["板块", "数量"]
            board_counts["占比"] = (board_counts["数量"] / total * 100).round(1).astype(str) + "%"
            
            lines += [
                "",
                "## 板块分布",
                "",
                board_counts.to_markdown(index=False),
            ]
        
        # 行业统计
        if "行业" in candidates.columns:
            industry_counts = candidates["行业"].value_counts().reset_index()
            industry_counts.columns = ["行业", "数量"]
            industry_counts["占比"] = (industry_counts["数量"] / total * 100).round(1).astype(str) + "%"
            
            # 只显示前15个行业
            if len(industry_counts) > 15:
                top_industries = industry_counts.head(15)
                other_count = industry_counts.iloc[15:]["数量"].sum()
                other_pct = (other_count / total * 100).round(1)
                lines += [
                    "",
                    "## 行业分布（Top 15）",
                    "",
                    top_industries.to_markdown(index=False),
                    "",
                    f"*其他 {len(industry_counts) - 15} 个行业共 {other_count} 只，占比 {other_pct}%*",
                ]
            else:
                lines += [
                    "",
                    "## 行业分布",
                    "",
                    industry_counts.to_markdown(index=False),
                ]
        
        return lines
