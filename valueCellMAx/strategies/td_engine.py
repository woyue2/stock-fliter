"""
TD 策略引擎 (Portable)
用于在 ValueCellMAx 中生成和管理 TD 信号。
"""
import pandas as pd
import os
import streamlit as st
import json
from typing import Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
from util.indicators_lib import TechnicalIndicators
from util.td_core import TDCore
from util.db import get_daily_data, get_stock_info_map, upsert_strategy_signals, get_strategy_signals
from util.system_utils import get_optimal_worker_count

def _worker_td_scan(code: str, target_date: str) -> Optional[dict]:
    """子进程执行单个股票的 TD 扫描"""
    try:
        # 获取足够的历史数据
        df_daily = get_daily_data(code, days=400)
        if df_daily.empty:
            return None
            
        df_daily['date_str'] = df_daily['date'].dt.strftime('%Y-%m-%d')
        if target_date not in df_daily['date_str'].values:
            return None
            
        df_cutoff = df_daily[df_daily['date_str'] <= target_date].copy()
        if df_cutoff.empty:
            return None
            
        # 计算 TD 计数 (使用统一的核心逻辑)
        res = TDCore.full_analyze(df_cutoff)
        
        if res['共振级别'] != "无底部信号":
            return {
                'code': code,
                'date': target_date,
                'strategy_name': 'TD',
                'signal_type': res['共振级别'],
                'score': res['底部权重'],
                'extra_info': json.dumps(res, ensure_ascii=False) # 存储完整分析 JSON
            }
    except Exception:
        pass
    return None

def run_td_analysis_for_date(target_date: str, limit: int = None, progress_callback=None) -> int:
    """
    为指定日期运行 TD 全量扫描并保存结果到数据库。
    优化：使用多进程加速扫描过程。
    """
    stocks = get_stock_info_map()
    if limit:
        keys = list(stocks.keys())[:limit]
        stocks = {k: stocks[k] for k in keys}
    
    total = len(stocks)
    signals = []
    
    # 获取最优进程数
    workers = get_optimal_worker_count()
    
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_code = {
                executor.submit(_worker_td_scan, code, target_date): code 
                for code in stocks
            }
            
            for i, future in enumerate(as_completed(future_to_code)):
                if progress_callback:
                    progress_callback(i + 1, total)
                res = future.result()
                if res:
                    signals.append(res)
    else:
        # 串行兜底
        for i, code in enumerate(stocks):
            if progress_callback:
                progress_callback(i + 1, total)
            res = _worker_td_scan(code, target_date)
            if res:
                signals.append(res)
            
    if signals:
        upsert_strategy_signals(signals)
        
    return len(signals)

@st.cache_data(ttl="1h", show_spinner=False)
def _cached_stock_analyze(code: str, target_date: str) -> Optional[dict]:
    """缓存单只股票在特定日期的深度分析结果"""
    df_daily = get_daily_data(code, days=400)
    if df_daily.empty:
        return None
        
    df_daily['date_str'] = df_daily['date'].dt.strftime('%Y-%m-%d')
    df_cutoff = df_daily[df_daily['date_str'] <= target_date].copy()
    if df_cutoff.empty:
        return None
        
    # 执行深度分析 (获取共振级别、权重、详情、各周期计数等)
    analysis = TDCore.full_analyze(df_cutoff)
    return analysis

def get_detailed_td_results(target_date: str, limit: int = None, progress_callback=None) -> pd.DataFrame:
    """
    获取详细的 TD 分析结果（返回 DataFrame，供 UI 展示）
    优化逻辑：直接从数据库读取存储好的 JSON 详情，实现秒开。
    """
    # 1. 直接从数据库获取已存储的完整信号 (包含 extra_info JSON)
    existing_signals = get_strategy_signals(target_date, "TD")
    
    if not existing_signals:
        return pd.DataFrame()
        
    if limit:
        existing_signals = existing_signals[:limit]
        
    results = []
    
    # 2. 解析存储的 JSON 数据
    for sig in existing_signals:
        extra_info_str = sig.get('extra_info')
        if not extra_info_str:
            # 兼容旧数据：如果没有 extra_info，才回退到缓存分析逻辑
            code = sig['code']
            analysis = _cached_stock_analyze(code, target_date)
        else:
            try:
                analysis = json.loads(extra_info_str)
            except Exception:
                analysis = None
        
        if analysis:
            res = analysis.copy()
            res.update({
                '代码': sig['code'],
                '名称': sig.get('name', '未知'),
                '日期': target_date,
                '日/周/月 TD计数': f"{res.get('日TD计数', 0)} / {res.get('周TD计数', 0)} / {res.get('月TD计数', 0)}"
            })
            results.append(res)
            
    if not results:
        return pd.DataFrame()
        
    df_results = pd.DataFrame(results)
    
    # 按照原型中的顺序和字段进行格式化
    column_order = [
        "代码", "名称", "共振级别", "底部详情", "底部权重", 
        "日/周/月 TD计数", "波动率", "日最新价"
    ]
    
    return df_results[[c for c in column_order if c in df_results.columns]].sort_values(by="底部权重", ascending=False)
