"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

INPUT: 配置文件或命令行参数
OUTPUT: DataFrame 包含板块、涨幅、成交额、主力净额、散户净额
"""
import pandas as pd
import logging
import os

logger = logging.getLogger(__name__)

def load_data(is_test: bool = False) -> pd.DataFrame:
    """
    为了演示A*B*C博弈逻辑，如果为测试模式，则返回硬编码或者构建的测试集。
    未来可以对接 akshare 的资金流向接口。
    """
    if is_test:
        logger.info("Test mode enabled. Loading mock sector data for zhulistrength.")
        data = [
            {"序号": 1, "板块": "上证指数", "涨幅": 0.64, "成交额": 10680.44, "主力净额": 26.14, "散户净额": -281.56},
            {"序号": 32, "板块": "固态电池", "涨幅": 1.19, "成交额": 1683.36, "主力净额": 39.99, "散户净额": -96.78},
            {"序号": 39, "板块": "短剧游戏", "涨幅": 1.45, "成交额": 415.07, "主力净额": 24.33, "散户净额": -43.55},
            {"序号": 40, "板块": "可控核聚变", "涨幅": 2.60, "成交额": 1189.36, "主力净额": 68.63, "散户净额": -49.36},
            {"序号": 14, "板块": "文化传媒", "涨幅": 1.35, "成交额": 250.96, "主力净额": 0.28, "散户净额": -7.25},
            {"序号": 10, "板块": "电力", "涨幅": 1.75, "成交额": 716.66, "主力净额": 7.80, "散户净额": 10.08},
            {"序号": 2, "板块": "油气采服", "涨幅": -4.96, "成交额": 579.57, "主力净额": -9.87, "散户净额": -9.82},
        ]
        return pd.DataFrame(data)
    else:
        logger.warning("Normal mode not fully implemented (requires real fund flow source). Returning empty DF.")
        return pd.DataFrame()
