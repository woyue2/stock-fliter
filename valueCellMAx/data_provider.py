"""
[INPUT]:    code (str), days (int)
[OUTPUT]:   pd.DataFrame
[POS]:      valueCellMAx/data_provider.py - Data access layer
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""
import sys
import os
import streamlit as st
import pandas as pd
from datetime import datetime

# 将项目根目录加入 path 以便导入 util
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from util.db import (
    get_daily_data, get_stock_info_map, get_journal_note, 
    upsert_journal_note, ensure_schema, get_db_path, 
    get_chart_annotations, add_chart_annotation, delete_chart_annotation,
    get_strategy_signals, get_available_strategies
)

# 初始化数据库表结构
ensure_schema()

def check_db_health():
    """检查 SQLite 数据库是否健康（存在且有数据）"""
    db_path = get_db_path()
    if not db_path.exists():
        return False, f"数据库文件不存在: {db_path}"
    
    # 获取股票映射，如果空则说明没数据
    info_map = get_stock_info_map()
    if not info_map:
        return False, "数据库中暂无股票元数据，请先运行数据抓取或迁移脚本。"
    
    return True, "健康"

@st.cache_data(ttl="1h", show_spinner=False)
def get_market_calendar():
    """从数据库获取全局交易日历 (缓存版)"""
    from util.db import _connect
    try:
        with _connect() as conn:
            df = pd.read_sql_query("SELECT DISTINCT date FROM daily_ohlcv ORDER BY date ASC", conn)
            return df['date'].tolist()
    except Exception:
        return []

@st.cache_data(ttl="1h", show_spinner=False)
def get_stock_list():
    """获取所有可用股票列表 (缓存版)"""
    info_map = get_stock_info_map()
    if not info_map:
        return []
    return sorted([f"[{code}] {info['name']}" for code, info in info_map.items()])

@st.cache_data(ttl="10m", show_spinner="正在读取数据...")
def get_clean_df(stock_str: str, days: int = 2000):
    """获取并清洗 OHLCV 数据 (缓存版)"""
    code = stock_str.split(']')[0].replace('[', '').strip()
    df = get_daily_data(code, days=days)
    if df.empty:
        return pd.DataFrame()
    
    df = df.rename(columns={
        'date': 'time',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'volume'
    })
    
    if not pd.api.types.is_datetime64_any_dtype(df['time']):
        df['time'] = pd.to_datetime(df['time'])
        
    return df.sort_values('time')

def get_available_dates(df):
    """获取所有可用的交易日期字符串列表"""
    if df.empty:
        return []
    return df['time'].dt.strftime('%Y-%m-%d').tolist()

def get_stock_note(code: str) -> str:
    """从数据库获取复盘笔记"""
    return get_journal_note(code)

def save_stock_note(code: str, note: str) -> None:
    """保存复盘笔记到数据库"""
    upsert_journal_note(code, note)

def get_stock_annotations(code: str):
    """获取所有图表注解"""
    return get_chart_annotations(code)

def add_stock_annotation(code: str, date: str, text: str, price: float = None):
    """添加图表注解"""
    add_chart_annotation(code, date, text, price)

def remove_stock_annotation(code: str, date: str, text: str):
    """删除图表注解"""
    delete_chart_annotation(code, date, text)

def get_stock_list_by_strategy(strategy_name: str, signal_type: str, date: str):
    """通过策略和日期获取筛选后的股票列表"""
    # 策略名为 "None" 时返回全量
    if strategy_name == "无" or not strategy_name:
        return get_stock_list()
        
    signals = get_strategy_signals(date, strategy_name)
    if not signals:
        return []
        
    # 如果指定了信号类型 (且不是 "全选")，进一步过滤
    if signal_type and signal_type != "全部":
        signals = [s for s in signals if s['signal_type'] == signal_type]
        
    # 返回格式化列表: [代码] 名称 (信号)
    return sorted([f"[{s['code']}] {s['name']} ({s['signal_type']})" for s in signals])

def get_signal_types_for_strategy(date: str, strategy_name: str):
    """获取指定日期某策略产生的所有信号类型(用于二级菜单)"""
    signals = get_strategy_signals(date, strategy_name)
    if not signals:
        return []
    return sorted(list(set([s['signal_type'] for s in signals])))

def run_strategy_scan(strategy_name: str, target_date: str, limit: int = None, progress_callback=None):
    """运行策略扫描并存库"""
    if strategy_name == "TD":
        from strategies.td_engine import run_td_analysis_for_date
        return run_td_analysis_for_date(target_date, limit=limit, progress_callback=progress_callback)
    return 0

def get_strategy_full_results(strategy_name: str, target_date: str, limit: int = None, _progress_callback=None):
    """获取策略的详细分析结果 DataFrame"""
    if strategy_name == "TD":
        from strategies.td_engine import get_detailed_td_results
        return get_detailed_td_results(target_date, limit=limit, progress_callback=_progress_callback)
    return pd.DataFrame()
