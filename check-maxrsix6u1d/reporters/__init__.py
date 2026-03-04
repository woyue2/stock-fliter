# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  None
# OUTPUT: None
# POS:    check-maxrsix6u1d/reporters/__init__.py
# -*- coding: utf-8 -*-
"""报告生成器模块"""
from .markdown_reporter import MarkdownReporter
from .html_reporter import HtmlReporter

__all__ = ["MarkdownReporter", "HtmlReporter"]
