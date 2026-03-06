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
    优先加载【板块指标】(BK_ 前缀) 的真实行情与资金流数据。
    如果没有板块指标，则自动汇总个股数据作为备选方案。
    """
    try:
        from util.db import _connect, get_stock_info_map
        
        # 1. 尝试直接加载【板块指标】(真实板块/概念数据)
        sql_bk = """
        SELECT * FROM (
            SELECT 
                ff.code,
                ff.date,
                ff.main_net AS 主力净额,
                ff.retail_net AS 散户净额,
                ohlcv.amount AS 成交额,
                ohlcv.pctchg AS 涨幅,
                ROW_NUMBER() OVER (PARTITION BY ff.code ORDER BY ff.date DESC) as rn
            FROM daily_fund_flow ff
            LEFT JOIN daily_ohlcv ohlcv ON ff.code = ohlcv.code AND ff.date = ohlcv.date
            WHERE ff.code LIKE 'BK_%'
        ) WHERE rn = 1
        """
        
        with _connect() as conn:
            sector_df = pd.read_sql_query(sql_bk, conn)
            
        if not sector_df.empty:
            info_map = get_stock_info_map()
            sector_df['板块'] = sector_df['code'].apply(lambda x: info_map.get(x, {}).get('name', x.replace('BK_', '')))
            logger.info(f"Loaded {len(sector_df)} real sector indices (Concepts/Industries).")
            return sector_df[['date', '板块', '涨幅', '成交额', '主力净额', '散户净额']]

        # 2. 备选方案：聚合个股数据
        logger.info("No sector indices found. Falling back to stock aggregation.")
        sql_stocks = """
        SELECT * FROM (
            SELECT 
                ff.code, ff.date,
                ff.main_net AS 主力存量,
                ff.retail_net AS 散户存量,
                ohlcv.amount AS 个股成交额,
                ohlcv.pctchg AS 个股涨幅,
                ROW_NUMBER() OVER (PARTITION BY ff.code ORDER BY ff.date DESC) as rn
            FROM daily_fund_flow ff
            LEFT JOIN daily_ohlcv ohlcv ON ff.code = ohlcv.code AND ff.date = ohlcv.date
            WHERE ff.code NOT LIKE 'BK_%'
        ) WHERE rn = 1
        """
        
        with _connect() as conn:
            df_stocks = pd.read_sql_query(sql_stocks, conn)
            
        if df_stocks.empty:
            return pd.DataFrame()

        info_map = get_stock_info_map()
        df_stocks['行业名称'] = df_stocks['code'].apply(lambda x: info_map.get(x, {}).get('industry', '未知行业'))
        
        sector_group = df_stocks.groupby('行业名称').agg({
            'date': 'max',
            '主力存量': 'sum',
            '散户存量': 'sum',
            '个股成交额': 'sum',
            '个股涨幅': 'mean'
        }).reset_index()

        res_df = pd.DataFrame()
        res_df['date'] = sector_group['date']
        res_df['板块'] = sector_group['行业名称']
        res_df['涨幅'] = sector_group['个股涨幅']
        res_df['成交额'] = sector_group['个股成交额']
        res_df['主力净额'] = sector_group['主力存量']
        res_df['散户净额'] = sector_group['散户存量']
        return res_df[~res_df['板块'].isin(['未知行业', '未知'])]

    except Exception as e:
        logger.error(f"加载数据失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return pd.DataFrame()
