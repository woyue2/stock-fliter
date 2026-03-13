# -*- coding: utf-8 -*-
"""
TD 策略核心逻辑 (TD Strategy Core Logic)
提取自 check-td/analyzers/td_analyzer.py，用于多处共享。
"""
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from util.indicators_lib import TechnicalIndicators

class TDCore:
    """TD 核心逻辑类"""

    @staticmethod
    def get_td_level(td_count: int) -> str:
        """根据 TD 计数返回级别名称"""
        if td_count >= 20: return f"{td_count}底(20+极限)"
        if td_count >= 15: return f"{td_count}底(15-20极地)"
        if td_count >= 10: return f"{td_count}底(10-15深底)"
        if td_count >= 6: return f"{td_count}底"
        return "无"

    @staticmethod
    def get_last_high_td(sequence: pd.Series, df: pd.DataFrame) -> Tuple[str, Optional[float]]:
        """获取最近的高位 TD 信号日期和价格"""
        for idx in range(len(sequence) - 1, -1, -1):
            if sequence.iloc[idx] >= 6:
                row = df.iloc[idx]
                return pd.Timestamp(row["date"]).strftime("%Y-%m-%d"), round(float(row["close"]), 2)
        return "", None

    @staticmethod
    def analyze_period(df: pd.DataFrame, prefix: str) -> Dict:
        """分析单个周期的基本数据"""
        if df.empty:
            return {
                f"{prefix}最新日期": "", f"{prefix}最新价": None,
                f"{prefix}最高价": None, f"{prefix}最低价": None, f"{prefix}均价": None,
            }
        last_row = df.iloc[-1]
        return {
            f"{prefix}最新日期": pd.Timestamp(last_row["date"]).strftime("%Y-%m-%d"),
            f"{prefix}最新价": round(float(last_row["close"]), 2),
            f"{prefix}最高价": round(float(df["high"].max()), 2),
            f"{prefix}最低价": round(float(df["low"].min()), 2),
            f"{prefix}均价": round(float(df["close"].mean()), 2),
        }

    @staticmethod
    def get_td_info(df: pd.DataFrame, prefix: str) -> Dict:
        """获取单个周期的 TD 详细信息"""
        if df.empty or "close" not in df.columns:
            return {
                f"{prefix}TD计数": 0, f"{prefix}9底": False, f"{prefix}8底": False,
                f"{prefix}7底": False, f"{prefix}6底": False, f"{prefix}底部级别": "无",
                f"{prefix}最近高底日期": "", f"{prefix}最近高底价格": None,
            }

        close_series = df["close"].reset_index(drop=True).astype(float)
        sequence = TechnicalIndicators.calculate_td_sequence(close_series)
        td_count = int(sequence.iloc[-1]) if not sequence.empty else 0
        
        last_dt, last_price = TDCore.get_last_high_td(sequence, df)
        
        return {
            f"{prefix}TD计数": td_count,
            f"{prefix}9底": td_count >= 9,
            f"{prefix}8底": td_count >= 8,
            f"{prefix}7底": td_count >= 7,
            f"{prefix}6底": td_count >= 6,
            f"{prefix}底部级别": TDCore.get_td_level(td_count),
            f"{prefix}最近高底日期": last_dt,
            f"{prefix}最近高底价格": last_price,
        }

    @staticmethod
    def _comb(label: str, val: int, req_idx: List[int], counts: List[int]) -> Optional[Tuple[str, int]]:
        """检查特定的共振组合"""
        if all(counts[i] >= val for i in req_idx):
            return (label, val)
        return None

    @staticmethod
    def build_combinations(c: List[int]) -> List[Tuple[str, int]]:
        """构建所有可能的共振组合"""
        combos = []
        max_val = max(c) if c else 0
        if max_val < 6:
            return []
            
        for val in range(max_val, 5, -1):
            combos.append(TDCore._comb("日周月", val, [0, 1, 2], c))
            combos.append(TDCore._comb("日周", val, [0, 1], c))
            combos.append(TDCore._comb("日月", val, [0, 2], c))
            combos.append(TDCore._comb("周月", val, [1, 2], c))
            combos.append(TDCore._comb("日", val, [0], c))
            combos.append(TDCore._comb("周", val, [1], c))
            combos.append(TDCore._comb("月", val, [2], c))
        
        return [cb for cb in combos if cb]

    @staticmethod
    def build_resonance(daily: int, weekly: int, monthly: int) -> Dict:
        """构建最终的共振级别和权重"""
        combinations = TDCore.build_combinations([daily, weekly, monthly])
        
        def get_group_rank(val):
            if val >= 20: return 6
            if val >= 15: return 5
            if val >= 10: return 4
            return (val - 6) # (9->3, 8->2, 7->1, 6->0)
        
        def get_resonance_rank(label):
            return len(label)

        def get_total_priority(x):
            label, val = x
            return get_group_rank(val) * 10000 + get_resonance_rank(label) * 1000 + val

        combinations.sort(key=get_total_priority, reverse=True)
        
        if not combinations:
            return {
                "共振级别": "无底部信号",
                "底部详情": "无",
                "底部权重": 0,
                "9底及以上周期数": 0
            }

        top_label, top_val = combinations[0]
        
        group_suffix = ""
        if top_val >= 20: group_suffix = "(20+极限)"
        elif top_val >= 15: group_suffix = "(15-20极地)"
        elif top_val >= 10: group_suffix = "(10-15深底)"
        
        level = f"{top_label}{top_val}底{group_suffix}"
        detail_str = " + ".join(f"{n}{v}" for n, v in combinations[:5])
        
        return {
            "9底及以上周期数": sum(c >= 9 for c in [daily, weekly, monthly]),
            "共振级别": level,
            "底部详情": detail_str,
            "底部权重": get_total_priority(combinations[0])
        }

    @staticmethod
    def full_analyze(df_daily: pd.DataFrame) -> Dict:
        """执行全量 TD 分析 (包含日周月、共振、波动率)"""
        df_daily = df_daily.copy()
        df_weekly = TechnicalIndicators.resample_ohlcv(df_daily, "W")
        try:
            df_monthly = TechnicalIndicators.resample_ohlcv(df_daily, "ME") 
        except Exception:
            df_monthly = TechnicalIndicators.resample_ohlcv(df_daily, "M")
            
        result = {}
        for df, prefix in [(df_daily, "日"), (df_weekly, "周"), (df_monthly, "月")]:
            result.update(TDCore.analyze_period(df, prefix))
            result.update(TDCore.get_td_info(df, prefix))
            
        result.update(TDCore.build_resonance(
            result["日TD计数"], result["周TD计数"], result["月TD计数"]
        ))
        
        if "high" in df_daily.columns and "low" in df_daily.columns:
            vol = TechnicalIndicators.calculate_parkinson_volatility(df_daily["high"], df_daily["low"], window=20)
            result["波动率"] = round(vol, 4)
        else:
            result["波动率"] = 0.0
            
        return result
