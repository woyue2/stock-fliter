# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  code: str — 6位股票代码；board: Optional[str] — 板块名称（可选）
# OUTPUT: str — 东方财富行情页面 URL
# POS:    util/url_utils.py（从 check-maxrsix6u1d/utils.py 提升，Phase 5）
# -*- coding: utf-8 -*-
"""
东方财富 URL 工具函数

提供股票代码 → 市场前缀 → eastmoney URL 的转换。
迁移自 check-maxrsix6u1d/utils.py，统一供所有 check-* 模块使用。

约束：只依赖标准库，绝不 import check-* 模块（防循环依赖）。
"""
from __future__ import annotations

from typing import Optional


def infer_market_prefix(code: str, board: Optional[str] = None) -> str:
    """
    推断东方财富市场前缀 (sh/sz/bj)

    优先按板块名称判断，其次按代码首位数字判断。

    Args:
        code:  6位股票代码，如 "600519"
        board: 板块名称，如 "上海主板"、"创业板"（可选）

    Returns:
        市场前缀字符串："sh" | "sz" | "bj"
    """
    board = (board or "").strip()
    if board in {"上海主板", "科创板"}:
        return "sh"
    if board in {"深圳主板", "创业板"}:
        return "sz"
    if board in {"北交所", "北京交易所"}:
        return "bj"
    if code.startswith("6"):
        return "sh"
    if code.startswith("8"):
        return "bj"
    return "sz"


def get_eastmoney_url(code: str, board: Optional[str] = None) -> str:
    """
    获取东方财富股票行情页面 URL

    Args:
        code:  6位股票代码，如 "600519"
        board: 板块名称（可选，用于更精确地判断市场前缀）

    Returns:
        URL 字符串，如 "https://quote.eastmoney.com/sh600519.html"
    """
    prefix = infer_market_prefix(code, board)
    return f"https://quote.eastmoney.com/{prefix}{code}.html"
