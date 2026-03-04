# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  pd.DataFrame — 单股日线数据；Dict — stock_info(code/name/industry)
# OUTPUT: Optional[Dict] — 含 21 个布尔策略列 + 基础指标的分析结果
# POS:    check-indicator-combo/analyzers/__init__.py
"""
analyzers 包入口

暴露 StockAnalyzer 为外部入口点。
"""
from .combo_analyzer import StockAnalyzer, get_board_type

__all__ = ["StockAnalyzer", "get_board_type"]
