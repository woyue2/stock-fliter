# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  pd.DataFrame — 单股日线数据；end_date: Optional[str]
# OUTPUT: Tuple[Optional[dict], Optional[str]]
# POS:    check-volupxyangxshipan/analyzers/__init__.py
"""
analyzers 包入口

暴露 evaluate_stock 和 empty_result_df 为标准接口。
"""
from .volup_yang_shipan_analyzer import evaluate_stock, empty_result_df

__all__ = ["evaluate_stock", "empty_result_df"]
