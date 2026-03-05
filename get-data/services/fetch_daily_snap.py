# -*- coding: utf-8 -*-
"""
[L3] fetch_daily_snap.py
[ROLE]: 极速获取 A 股当日行情快照并入库
[INPUT]: 新浪财经 API
[OUTPUT]: SQLite stocks.db (upsert)
[PROTOCOL]: 变更时更新此头部，然后检查 L2/CLAUDE.md

【极速版】每日收盘后行情更新 (基于新浪财经全市场快照)
运行一次仅需 3 秒，直接填充今天全市场的日 K 线到 SQLite 数据库。
不需要跑原有的 45 分钟 fetch_daily_history.py (那个只在补长达几个月历史数据时才用)。
"""
import sys
import time
import requests
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from tqdm import tqdm

# 确保能找到 util.db
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 导入 SQLite 双写接口
from util.db import upsert_daily_rows

# 新浪财经沪深A股节点
SINA_API_URL = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "http://finance.sina.com.cn/stock/quotes/center/hsa.html"
}

def fetch_page(page_num: int, num_per_page: int = 80) -> list:
    # 稍微增加随机延迟，避免被新浪 456 封印
    import random
    time.sleep(random.uniform(0.1, 0.5))
    params = {
        "page": page_num,
        "num": num_per_page,
        "sort": "symbol",
        "asc": 1,
        "node": "hs_a"  # 沪深A股
    }
    try:
        res = requests.get(SINA_API_URL, params=params, headers=HEADERS, timeout=10)
        data = res.json()
        if isinstance(data, list):
            return data
    except Exception as e:
        print(f"\n[Error] Page {page_num} fetch failed: {e}")
    return []

def run_fast_update():
    print("🚀 [FastUpdate] 开始极速全市场快照拉取...")
    start_time = time.time()
    
    # 按照 80 只一页，全市场大约 5000 多只，抓 70 页就够覆盖了
    total_pages = 70
    all_raw_data = []

    # 1. 降低并发数 (从 20 降到 3)，增加稳定性，防止触发新浪 456 拒访问
    print(f"📡 正在向新浪财经发起 {total_pages} 个页面请求 (低并发模式)...")
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fetch_page, page): page for page in range(1, total_pages + 1)}
        for future in tqdm(as_completed(futures), total=total_pages, desc="拉取进度"):
            page_data = future.result()
            if page_data:
                all_raw_data.extend(page_data)

    if not all_raw_data:
        print("❌ 未拉取到任何数据！请检查网络状态。")
        return

    print(f"✅ 成功拉取到 {len(all_raw_data)} 只股票快照，开始数据清洗入库...")
    
    # 2. 清洗数据并映射字段
    today_str = datetime.now().strftime("%Y-%m-%d")
    rows_for_db = []
    
    for item in all_raw_data:
        raw_code = item.get("symbol", "")
        # symbol 类似 "sh600000" 或 "bj920000", 我们只要纯数字
        code = "".join(filter(str.isdigit, raw_code))[-6:]
        if not code or not code.isdigit() or len(code) != 6:
            continue
            
        try:
            row = {
                "code": code,
                "date": today_str,
                "open": float(item.get("open", 0)),
                "high": float(item.get("high", 0)),
                "low": float(item.get("low", 0)),
                "close": float(item.get("trade", 0)),
                "volume": float(item.get("volume", 0)),
                "amount": float(item.get("amount", 0)),
                "pctchg": float(item.get("changepercent", 0)),
                "turn": float(item.get("turnoverratio", 0)),
            }
            # 过滤掉停牌/未交易的
            if row["volume"] > 0 and row["close"] > 0:
                rows_for_db.append(row)
        except (ValueError, TypeError):
            continue

    if not rows_for_db:
        print("⚠️ 未找到有效交易数据（节假日停牌或盘前？）")
        return

    # 3. 秒级入库 SQLite
    try:
        t_db = time.time()
        upsert_daily_rows(rows_for_db)
        print(f"💾 [SQLite] 成功将 {len(rows_for_db)} 条最新日 K 数据插入数据库！(耗时: {time.time()-t_db:.3f}秒)")
    except Exception as e:
        print(f"❌ 数据库写入失败: {e}")

    total_time = time.time() - start_time
    print(f"🎉 全部完成！总耗时: {total_time:.2f} 秒。")

if __name__ == "__main__":
    run_fast_update()
