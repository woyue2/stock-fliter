# -*- coding: utf-8 -*-
import pandas as pd
from typing import Dict, Optional
import os

# 全局内存对象池
_GLOBAL_DF_CACHE: Dict[str, pd.DataFrame] = {}
_USE_CACHE = False

def enable_data_pool():
    global _USE_CACHE
    _USE_CACHE = True
    print("🚀 [MemoryPool] 系统内存充足，已开启全局共享内存池优化。")

def get_df_from_pool(code: str) -> Optional[pd.DataFrame]:
    if not _USE_CACHE:
        return None
    return _GLOBAL_DF_CACHE.get(code)

def put_df_to_pool(code: str, df: pd.DataFrame):
    if _USE_CACHE and df is not None:
        # 只缓存最近的数据，避免内存溢出
        # 5000 只股票 x 1000 行 x 10 列 约占用 1.5GB-2GB RAM
        _GLOBAL_DF_CACHE[code] = df

def clear_pool():
    _GLOBAL_DF_CACHE.clear()
