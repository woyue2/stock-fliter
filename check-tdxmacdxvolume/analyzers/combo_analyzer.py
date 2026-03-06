# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  pd.DataFrame — 单股日线数据；Dict — stock_info(code/name/industry)
# OUTPUT: Optional[Dict] — 含布尔策略列 + 基础指标的分析结果
# POS:    check-tdxmacdxvolume/analyzers/combo_analyzer.py（重命名自 analyzer.py，Phase 3）
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
核心分析模块
实现23种策略的逻辑判断
"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

# Add util to path
util_dir = Path(__file__).resolve().parent.parent.parent / "util"
if str(util_dir) not in sys.path:
    sys.path.append(str(util_dir))

try:
    from indicators_lib import TechnicalIndicators
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
    from util.indicators_lib import TechnicalIndicators



def get_board_type(code: str) -> str:
    """根据股票代码获取板块类型"""
    if code.startswith('688'):
        return '科创板'
    if code.startswith('300') or code.startswith('301'):
        return '创业板'
    if code.startswith('8'):
        return '北交所'
    if code.startswith('002') or code.startswith('003'):
        return '深圳主板'
    if code.startswith('000'):
        return '深圳主板'
    if code.startswith('60'):
        return '上海主板'
    return '其他'


class StockAnalyzer:
    
    @staticmethod
    def analyze(df: pd.DataFrame, stock_info: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        分析单只股票
        
        Args:
            df: 日线数据 DataFrame
            stock_info: 股票基本信息 (code, name)
            
        Returns:
            分析结果字典
        """
        if df is None or df.empty or len(df) < 60:
            return None
            
        close = df["close"]
        volume = df["volume"]
        date = df["date"].iloc[-1]
        
        # 1. 计算基础指标
        # MAxRSIx6U1D
        steady_df = TechnicalIndicators.check_steady_uptrend(close)
        is_steady_uptrend = bool(steady_df["steady_uptrend"].iloc[-1])
        
        # 放量突破
        is_volume_breakout = TechnicalIndicators.check_volume_breakout(close, volume, df["high"])
        
        # MACD 零轴下金叉
        is_macd_gold = TechnicalIndicators.check_macd_golden_cross_below_zero(close)
        # 计算MACD强度（直接显示MACD值）
        macd_line, _, _ = TechnicalIndicators.calculate_macd(close)
        macd_value = macd_line.iloc[-1]
        macd_strength = round(macd_value, 4)  # 直接显示MACD值，保留4位小数
        
        # 检查MACD零轴下金叉（已计算一次，避免重复）
        
        # TD 序列 (寻找底部9)
        td_seq = TechnicalIndicators.calculate_td_sequence(close)
        td_count = td_seq.iloc[-1]
        is_td9 = td_count >= 9
        is_td8 = td_count >= 8
        is_td7 = td_count >= 7
        
        # 阴线判断 (收盘 < 开盘)
        open_price = df["open"].iloc[-1]
        is_red_day = close.iloc[-1] < open_price  # 阴线=True
        
        # 1. 计算所有基础指标（解耦）
        indicators = {
            "MAxRSIx6U1D": is_steady_uptrend,
            "放量突破": is_volume_breakout,
            "MACD金叉": is_macd_gold,
            "TD7": is_td7,
            "TD8": is_td8,
            "TD9": is_td9,
            "阴线": is_red_day
        }
        
        # 2. 组合策略（使用基础指标组合）
        strategies = []
        
        # 强买入信号（11个）
        if indicators["TD9"] and indicators["MACD金叉"] and indicators["放量突破"]:
            strategies.append("TD9+MACD金叉+放量突破")
            
        if indicators["TD9"] and indicators["MACD金叉"]:
            strategies.append("TD9+MACD金叉")
            
        if indicators["MAxRSIx6U1D"] and indicators["放量突破"]:
            strategies.append("MAxRSIx6U1D+放量突破")
            
        if indicators["TD9"] and indicators["放量突破"]:
            strategies.append("TD9+放量突破")
            
        if indicators["TD9"] and indicators["MACD金叉"] and indicators["阴线"]:
            strategies.append("TD9+MACD金叉+阴线")
            
        if indicators["TD9"] and indicators["MACD金叉"] and indicators["阴线"] and indicators["放量突破"]:
            strategies.append("TD9+MACD金叉+阴线+放量突破")
            
        if indicators["TD7"] and indicators["MACD金叉"]:
            strategies.append("TD7+MACD金叉")
            
        if indicators["TD8"] and indicators["MACD金叉"]:
            strategies.append("TD8+MACD金叉")
            
        if indicators["TD7"] and indicators["放量突破"]:
            strategies.append("TD7+放量突破")
            
        if indicators["TD8"] and indicators["放量突破"]:
            strategies.append("TD8+放量突破")
            
        if indicators["TD8"] and indicators["MACD金叉"] and indicators["阴线"] and indicators["放量突破"]:
            strategies.append("TD8+MACD金叉+阴线+放量突破")
        
        # 中买入信号（6个）
        if indicators["MACD金叉"] and indicators["放量突破"]:
            strategies.append("MACD金叉+放量突破")
            
        if (not indicators["MAxRSIx6U1D"]) and indicators["MACD金叉"]:
            strategies.append("非MAxRSIx6U1D+MACD金叉")
            
        if indicators["TD9"] and indicators["MAxRSIx6U1D"]:
            strategies.append("TD9+MAxRSIx6U1D")
            
        if indicators["TD7"] and indicators["MACD金叉"] and indicators["阴线"]:
            strategies.append("TD7+MACD金叉+阴线")
            
        if indicators["TD8"] and indicators["MACD金叉"] and indicators["阴线"]:
            strategies.append("TD8+MACD金叉+阴线")
            
        if indicators["TD9"] and indicators["MACD金叉"] and indicators["阴线"]:
            strategies.append("TD9+MACD金叉+阴线")
        
        # 观察信号（4个）
        if indicators["MAxRSIx6U1D"] and indicators["MACD金叉"]:
            strategies.append("MAxRSIx6U1D+MACD金叉")
            
        if indicators["MAxRSIx6U1D"] and (not indicators["放量突破"]):
            strategies.append("MAxRSIx6U1D+非放量突破")
            
        if indicators["TD9"] or indicators["MACD金叉"]:
            strategies.append("TD9或MACD金叉")
            
        if indicators["TD7"] and indicators["MACD金叉"] and indicators["阴线"] and indicators["放量突破"]:
            strategies.append("TD7+MACD金叉+阴线+放量突破")
        
        # 如果没有任何策略命中，则忽略
        if not strategies:
            return None
            
        # 3. 构建结果（包含所有基础指标和策略命中）
        result = {
            "代码": stock_info.get("code"),
            "名称": stock_info.get("name"),
            "板块": get_board_type(stock_info.get("code", "")),
            "行业": stock_info.get("industry", ""),
            "最新日期": date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date),
            "最新收盘": round(float(close.iloc[-1]), 2),
            "MACD值": macd_strength,
            "TD计数": int(td_count),
            # 基础指标
            "MAxRSIx6U1D": indicators["MAxRSIx6U1D"],
            "放量突破": indicators["放量突破"],
            "MACD金叉": indicators["MACD金叉"],
            "TD7": indicators["TD7"],
            "TD8": indicators["TD8"],
            "TD9": indicators["TD9"],
            "阴线": indicators["阴线"],
            # 策略命中
            "所属策略": ",".join(strategies),
            # 各策略命中状态（用于HTML筛选）
            "TD9+MACD金叉+放量突破": "TD9+MACD金叉+放量突破" in strategies,
            "TD9+MACD金叉": "TD9+MACD金叉" in strategies,
            "MAxRSIx6U1D+放量突破": "MAxRSIx6U1D+放量突破" in strategies,
            "TD9+放量突破": "TD9+放量突破" in strategies,
            "TD9+MACD金叉+阴线": "TD9+MACD金叉+阴线" in strategies,
            "TD9+MACD金叉+阴线+放量突破": "TD9+MACD金叉+阴线+放量突破" in strategies,
            "TD7+MACD金叉": "TD7+MACD金叉" in strategies,
            "TD8+MACD金叉": "TD8+MACD金叉" in strategies,
            "TD7+放量突破": "TD7+放量突破" in strategies,
            "TD8+放量突破": "TD8+放量突破" in strategies,
            "TD8+MACD金叉+阴线+放量突破": "TD8+MACD金叉+阴线+放量突破" in strategies,
            "MACD金叉+放量突破": "MACD金叉+放量突破" in strategies,
            "非MAxRSIx6U1D+MACD金叉": "非MAxRSIx6U1D+MACD金叉" in strategies,
            "TD9+MAxRSIx6U1D": "TD9+MAxRSIx6U1D" in strategies,
            "TD7+MACD金叉+阴线": "TD7+MACD金叉+阴线" in strategies,
            "TD8+MACD金叉+阴线": "TD8+MACD金叉+阴线" in strategies,
            "TD9+MACD金叉+阴线": "TD9+MACD金叉+阴线" in strategies,
            "MAxRSIx6U1D+MACD金叉": "MAxRSIx6U1D+MACD金叉" in strategies,
            "MAxRSIx6U1D+非放量突破": "MAxRSIx6U1D+非放量突破" in strategies,
            "TD9或MACD金叉": "TD9或MACD金叉" in strategies,
            "TD7+MACD金叉+阴线+放量突破": "TD7+MACD金叉+阴线+放量突破" in strategies,
        }
        
        return result
