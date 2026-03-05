# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  filepaths / arguments
# OUTPUT: Series/DataFrame of stock data
# POS:    check-td/data_loader.py
# -*- coding: utf-8 -*-
"""
数据加载模块

提供统一的数据加载接口：
- 股票列表
- 日线数据（通过 util/db.get_daily_data）
- 行业信息
"""
from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional, Tuple
import re

import pandas as pd

import os
BASE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = BASE_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from util.db import get_daily_data as _db_get_daily  # noqa: E402
from util.db import get_stock_info_map as _db_get_info_map # noqa: E402

# 使用 centralized get-data 目录
GET_DATA_DIR = BASE_DIR.parent / "get-data"
DATA_DIR = GET_DATA_DIR / "data"
# 新增环境变量支持，加速并行分析时的 I/O
RAW_DIR = Path(os.environ.get("STOCK_RAW_DIR", str(DATA_DIR / "raw")))
OUTPUT_DIR = BASE_DIR / "output"


@dataclass
class StockItem:
    """股票信息"""
    code: str
    name: str
    bs_code: str
    industry: str = "未知"
    
    @property
    def market_prefix(self) -> str:
        """获取市场前缀 (sh/sz)"""
        if self.code.startswith('6'):
            return 'sh'
        return 'sz'


def ensure_dirs():
    """确保目录存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_board_type(code: str) -> str:
    """根据股票代码判断所属交易板块"""
    if code.startswith('688'):
        return '科创板'
    elif code.startswith('300') or code.startswith('301'):
        return '创业板'
    elif code.startswith('8'):
        return '北交所'
    elif code.startswith('002') or code.startswith('000'):
        return '深圳主板'
    elif code.startswith('60'):
        return '上海主板'
    else:
        return '其他'


def load_stock_info_map() -> dict:
    """加载股票信息映射 (code -> {name, industry})：优先 SQLite，fallback CSV。"""
    # 1. 优先尝试从数据库加载
    db_info = _db_get_info_map()
    if db_info:
        # 统一格式转换，确保 industry 不是 None
        for code in db_info:
            if not db_info[code].get("industry"):
                db_info[code]["industry"] = "未知"
        return db_info

    # 2. 如果数据库没有，则回退到 CSV
    info_map = {}
    paths = [DATA_DIR / "selected_stocks_all.csv", DATA_DIR / "selected_stocks.csv"]
    for path in paths:
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path, dtype=str)
            for _, row in df.iterrows():
                code = str(row.get("code", "")).strip()
                if not code: continue
                name = str(row.get("name", "")).strip()
                industry = str(row.get("industry", "")).strip()
                if industry.lower() == "nan": industry = ""
                if code not in info_map:
                    info_map[code] = {"name": name, "industry": industry}
                elif not info_map[code]["industry"] and industry:
                    info_map[code]["industry"] = industry
        except Exception:
            pass
    return info_map


def iter_stock_items(selected_path: Optional[Path] = None, limit: Optional[int] = None, from_raw: bool = False) -> Iterator[StockItem]:
    """
    迭代股票列表
    
    Args:
        selected_path: 股票列表文件路径，默认使用 data/selected_stocks.csv
        limit: 最多返回多少只股票
        from_raw: 是否直接遍历 raw 目录下的所有 csv 文件
        
    Yields:
        StockItem 对象
    """
    if from_raw:
        # 加载信息映射
        info_map = load_stock_info_map()
        
        # 遍历 raw 目录
        files = list(RAW_DIR.glob("*.csv"))
        count = 0
        for f in files:
            code = f.stem
            
            # 从映射中获取名称和行业
            info = info_map.get(code, {})
            name = info.get("name", code)
            industry = info.get("industry", "未知")
            
            bs_code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
            
            yield StockItem(code=code, name=name, bs_code=bs_code, industry=industry)
            
            count += 1
            if limit and count >= limit:
                break
        return

    if selected_path is None:
        # 优先使用 selected_stocks_all.csv
        selected_path = DATA_DIR / "selected_stocks_all.csv"
        
        if not selected_path.exists():
            selected_path = DATA_DIR / "selected_stocks.csv"
    
    if not selected_path.exists():
        raise FileNotFoundError(f"找不到股票列表文件: {selected_path}")
    
    df = pd.read_csv(selected_path, dtype=str)
    
    count = 0
    for _, row in df.iterrows():
        code = str(row.get("code", "")).strip()
        name = str(row.get("name", "")).strip()
        bs_code = str(row.get("bs_code", "")).strip()
        industry = str(row.get("industry", "未知")).strip()
        if industry.lower() == "nan": industry = "未知"
        
        if not code:
            continue
        
        # 补全 bs_code
        if not bs_code:
            prefix = "sh" if code.startswith('6') else "sz"
            bs_code = f"{prefix}.{code}"
        
        yield StockItem(code=code, name=name, bs_code=bs_code, industry=industry)
        
        count += 1
        if limit and count >= limit:
            break


def iter_raw_stock_items(limit: Optional[int] = None) -> Iterator[StockItem]:
    """
    直接遍历 raw 目录下的 CSV 文件作为股票列表
    
    Args:
        limit: 最多返回多少只股票
        
    Yields:
        StockItem 对象
    """
    if not RAW_DIR.exists():
        return
        
    # 加载名称映射（如果有的话）
    name_map = {}
    selected_path = DATA_DIR / "selected_stocks.csv"
    if not selected_path.exists():
        selected_path = DATA_DIR / "selected_stocks_all.csv"
        
    if selected_path.exists():
        try:
            df = pd.read_csv(selected_path, dtype={"code": str, "bs_code": str})
            for _, row in df.iterrows():
                c = str(row.get("code", "")).strip()
                n = str(row.get("name", "")).strip()
                if c and n:
                    name_map[c] = n
        except Exception:
            pass
            
    # 遍历 CSV 文件
    count = 0
    # 获取所有 csv 文件并按文件名排序，保证顺序一致
    csv_files = sorted(list(RAW_DIR.glob("*.csv")))
    
    for csv_file in csv_files:
        # 从文件名提取代码 (e.g. "600000.csv" -> "600000")
        code = csv_file.stem
        
        # 简单验证代码格式 (6位数字)
        if not re.match(r"^\d{6}$", code):
            continue
            
        name = name_map.get(code, "未知")
        prefix = "sh" if code.startswith('6') else "sz"
        bs_code = f"{prefix}.{code}"
        
        yield StockItem(code=code, name=name, bs_code=bs_code)
        
        count += 1
        if limit and count >= limit:
            break


def load_daily_data(code: str, days: int = 365) -> pd.DataFrame:
    """
    加载股票日线数据（SQLite 优先，fallback CSV）。

    Args:
        code: 股票代码
        days: 取最近 N 天的数据

    Returns:
        包含 date, open, high, low, close, volume 的 DataFrame
    """
    return _db_get_daily(code, days=days)


# BaoStock 模块缓存
_BAOSTOCK_MODULE = None
_BS_LOGGED_IN = False


def get_baostock():
    """获取 BaoStock 模块"""
    global _BAOSTOCK_MODULE
    if _BAOSTOCK_MODULE is None:
        try:
            _BAOSTOCK_MODULE = importlib.import_module("baostock")
        except ImportError:
            return None
    return _BAOSTOCK_MODULE


def login_baostock() -> bool:
    """登录 BaoStock"""
    global _BS_LOGGED_IN
    if _BS_LOGGED_IN:
        return True
    
    bs = get_baostock()
    if bs is None:
        return False
    
    try:
        lg = bs.login()
        if lg.error_code == "0":
            _BS_LOGGED_IN = True
            return True
    except Exception:
        pass
    return False


def logout_baostock():
    """登出 BaoStock"""
    global _BS_LOGGED_IN
    if not _BS_LOGGED_IN:
        return
    
    bs = get_baostock()
    if bs:
        try:
            bs.logout()
        except Exception:
            pass
    _BS_LOGGED_IN = False


def get_stock_industry(bs_code: str) -> str:
    """获取股票所属行业（证监会分类）"""
    bs = get_baostock()
    if bs is None:
        return "未知"
    
    try:
        rs = bs.query_stock_industry(code=bs_code)
        if rs.error_code == '0' and rs.next():
            data = rs.get_row_data()
            if len(data) > 3 and data[3]:
                # 去掉行业代码前缀，如"J66货币金融服务" -> "货币金融服务"
                return re.sub(r'^[A-Z]\d+', '', data[3]) or data[3]
        return '未知'
    except Exception:
        return '未知'


def find_latest_file(pattern: str, directory: Optional[Path] = None) -> Optional[Path]:
    """查找最新的匹配文件"""
    if directory is None:
        directory = OUTPUT_DIR
    
    files = sorted(directory.glob(pattern), reverse=True)
    return files[0] if files else None
