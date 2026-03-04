# -*- coding: utf-8 -*-
"""
工具函数模块
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import pandas as pd


def find_latest_file(output_dir: Path, pattern: str) -> Optional[Path]:
    """
    递归搜索最新的匹配文件，包括批次文件夹
    
    Args:
        output_dir: 输出目录
        pattern: 文件名模式（glob格式）
    
    Returns:
        最新匹配文件的路径，如果没找到返回None
    """
    # 先在根目录搜索（兼容旧文件）
    files = sorted(output_dir.glob(pattern), reverse=True)
    
    # 递归搜索批次文件夹中的文件
    batch_files = sorted(output_dir.glob(f"*/*/{pattern}"), reverse=True)
    
    # 合并并按路径（包含时间戳）排序
    all_files = files + batch_files
    return all_files[0] if all_files else None


def to_bool(value: object) -> bool:
    """将任意值转换为布尔值"""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y", "是"}


def read_csv_utf8(path: Path) -> pd.DataFrame:
    """读取CSV文件，自动处理编码问题"""
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


def normalize_code(code: str) -> str:
    """标准化股票代码（去除前缀如SH./SZ.）"""
    code_str = str(code).strip()
    if "." in code_str:
        return code_str.split(".")[-1]
    return code_str


def infer_market_prefix(code: str, board: Optional[str] = None) -> str:
    """推断市场前缀"""
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
    """获取东方财富股票页面URL"""
    prefix = infer_market_prefix(code, board)
    return f"https://quote.eastmoney.com/{prefix}{code}.html"
