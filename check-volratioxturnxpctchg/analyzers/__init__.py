# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  pd.DataFrame (日线), dict (股票信息)
# OUTPUT: dict (命中结果) | None (未命中)
# POS:    check-volratioxturnxpctchg/analyzers/__init__.py
# -*- coding: utf-8 -*-
"""
Analyzers 包入口 — 暴露 StockAnalyzer
"""
from .surge_analyzer import SurgeAnalyzer as StockAnalyzer

__all__ = ["StockAnalyzer"]
