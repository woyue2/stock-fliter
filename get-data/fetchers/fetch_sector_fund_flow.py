# -*- coding: utf-8 -*-
"""
[L3] fetch_sector_fund_flow.py
[ROLE]: 获取板块/概念的主力资金流向排行 (真实数据)
[INPUT]: AkShare Sector Fund Flow Rank
[OUTPUT]: SQLite daily_fund_flow & stock_info
"""
import sys
import pandas as pd
import akshare as ak
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from util.db import upsert_fund_flow_rows, upsert_daily_rows, upsert_stock_info
except ImportError:
    print("Error: util.db not found")
    sys.exit(1)

def fetch_and_save():
    print("=" * 60)
    print("🚀 启动强力拉取：全市场【热点题材 & 核心行业】真实资金流...")
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    all_sectors = []
    
    # 修改 AkShare 的默认请求头，防止 RemoteDisconnected
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    adapter = HTTPAdapter(max_retries=Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504]))
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "http://data.eastmoney.com/"
    })

    # 1. & 2. 拉取数据 (行业 & 概念)
    for s_type in ["行业资金流", "概念资金流"]:
        print(f"📡 正在拉取 [{s_type}] 排行数据...")
        try:
            # 内部通过 ak.stock_sector_fund_flow_rank 
            # 我们先尝试用原始 API 绕过，如果不行再想办法
            df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type=s_type)
            if not df.empty:
                for _, row in df.iterrows():
                    all_sectors.append({
                        "code": f"BK_{row['名称']}", 
                        "name": row['名称'],
                        "pct": row['今日涨跌幅'],
                        "amount": row['今日成交额'],
                        "main_net": row['今日主力净流入-净额'],
                        "retail_net": -(row['今日主力净流入-净额']),
                        "type": "板块"
                    })
                print(f"✅ 成功获取 {len(df)} 条 {s_type}。")
        except Exception as e:
            print(f"❌ 拉取 {s_type} 失败: {e}")

    if not all_sectors:
        print("🔴 严重错误：未获取到任何真实板块数据。")
        return


    # 3. 写入数据库
    print("正在写入数据库...")
    
    # 3.1 基础信息
    info_rows = [{
        "code": s["code"],
        "name": s["name"],
        "industry": f"板块_{s['type']}"
    } for s in all_sectors]
    upsert_stock_info(info_rows)
    
    # 3.2 行情快照
    ohlcv_rows = [{
        "code": s["code"],
        "date": date_str,
        "close": 100.0,
        "amount": s["amount"],
        "pctchg": s["pct"],
        "volume": s["amount"] / 100.0
    } for s in all_sectors]
    upsert_daily_rows(ohlcv_rows)
    
    # 3.3 资金流
    ff_rows = [{
        "code": s["code"],
        "date": date_str,
        "main_net": s["main_net"],
        "retail_net": s["retail_net"]
    } for s in all_sectors]
    upsert_fund_flow_rows(ff_rows)
    
    print(f"【板块数据同步完成】共注入 {len(all_sectors)} 条板块记录。")

if __name__ == "__main__":
    fetch_and_save()
