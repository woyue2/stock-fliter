import sys
from pathlib import Path
import pandas as pd
import logging

BASE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = BASE_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# 导入数据库接口
from util.db import _connect, get_stock_info_map

logger = logging.getLogger(__name__)

def load_data(is_test: bool = False) -> pd.DataFrame:
    """
    从 SQLite 数据库加载板块/股票的资金流向与行情快照数据。
    
    逻辑：
    1. 联合查询 daily_fund_flow (资金) 和 daily_ohlcv (行情)。
    2. 取每个 code 的最新日期数据。
    """
    sql = """
    WITH LatestDates AS (
        SELECT code, MAX(date) as max_date
        FROM daily_fund_flow
        GROUP BY code
    )
    SELECT 
        ff.code,
        ff.date,
        ff.main_net as 主力净额,
        ff.retail_net as 散户净额,
        ohlcv.close,
        ohlcv.amount as 成交额,
        ohlcv.pctchg as 涨幅
    FROM daily_fund_flow ff
    JOIN LatestDates ld ON ff.code = ld.code AND ff.date = ld.max_date
    LEFT JOIN daily_ohlcv ohlcv ON ff.code = ohlcv.code AND ff.date = ohlcv.date
    """
    
    try:
        from util.db import _connect
        with _connect() as conn:
            df = pd.read_sql_query(sql, conn)
            
        if df.empty:
            if is_test:
                logger.warning("DB 中没有资金流数据。请先运行种子脚本注入测试数据。")
            return pd.DataFrame()

        # 补全名称信息
        info_map = get_stock_info_map()
        df['板块'] = df['code'].apply(lambda x: info_map.get(x, {}).get('name', x))
        
        # 统一列名以适配 Analyzer
        # Analyzer 需要：板块, 涨幅, 成交额, 主力净额, 散户净额
        required_cols = ['板块', '涨幅', '成交额', '主力净额', '散户净额']
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0.0
                
        return df[required_cols]

    except Exception as e:
        logger.error(f"从 SQLite 加载资金流数据失败: {e}")
        return pd.DataFrame()
