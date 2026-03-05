import sys
from pathlib import Path
from datetime import datetime

# 确保能找到 util/db
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from util.db import upsert_fund_flow_rows, upsert_daily_rows, upsert_stock_info

def seed():
    print("正在注入 check-zhulistrength 样板数据到 SQLite...")
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # 样板数据
    mock_data = [
        {"code": "BK0001", "name": "上证指数", "涨幅": 0.64, "成交额": 10680.44, "主力净额": 26.14, "散户净额": -281.56},
        {"code": "BK0032", "name": "固态电池", "涨幅": 1.19, "成交额": 1683.36, "主力净额": 39.99, "散户净额": -96.78},
        {"code": "BK0039", "name": "短剧游戏", "涨幅": 1.45, "成交额": 415.07, "主力净额": 24.33, "散户净额": -43.55},
        {"code": "BK0040", "name": "可控核聚变", "涨幅": 2.60, "成交额": 1189.36, "主力净额": 68.63, "散户净额": -49.36},
        {"code": "BK0014", "name": "文化传媒", "涨幅": 1.35, "成交额": 250.96, "主力净额": 0.28, "散户净额": -7.25},
        {"code": "BK0010", "name": "电力", "涨幅": 1.75, "成交额": 716.66, "主力净额": 7.80, "散户净额": 10.08},
        {"code": "BK0002", "name": "油气采服", "涨幅": -4.96, "成交额": 579.57, "主力净额": -9.87, "散户净额": -9.82},
    ]

    # 1. 注入 stock_info
    info_rows = [{"code": d["code"], "name": d["name"], "industry": "行业指标"} for d in mock_data]
    upsert_stock_info(info_rows)
    
    # 2. 注入 daily_ohlcv (行情)
    ohlcv_rows = [{
        "code": d["code"],
        "date": date_str,
        "close": 10.0, # 随便填
        "amount": d["成交额"],
        "pctchg": d["涨幅"],
        "volume": d["成交额"] / 10 # 随便填
    } for d in mock_data]
    upsert_daily_rows(ohlcv_rows)
    
    # 3. 注入 daily_fund_flow (资金)
    ff_rows = [{
        "code": d["code"],
        "date": date_str,
        "main_net": d["主力净额"],
        "retail_net": d["散户净额"]
    } for d in mock_data]
    upsert_fund_flow_rows(ff_rows)
    
    print(f"注入完成。共 {len(mock_data)} 条记录。日期: {date_str}")

if __name__ == "__main__":
    seed()
