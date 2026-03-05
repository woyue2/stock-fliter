# -*- coding: utf-8 -*-
import sys
import os
import json
import time
from pathlib import Path
import pandas as pd
import requests
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "selected_stocks_all.csv"
CACHE_DIR = DATA_DIR / "cache"

def get_sina_concepts():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "sina_concept_mapping.json"
    
    today = time.strftime("%Y-%m-%d")
    if cache_file.exists():
        file_time = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(cache_file)))
        if file_time == today:
            print(f"[INFO] 发现当日新浪缓存，正在加载...")
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)

    print("[INFO] 正在获取新浪概念节点列表...")
    nodes_url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodes"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        res = requests.get(nodes_url, headers=headers, timeout=15)
        all_data = res.json()
    except Exception as e:
        print(f"[ERROR] 获取节点列表失败: {e}")
        return {}

    target_nodes = []
    
    def find_target_ids(data):
        if isinstance(data, list):
            # 新浪的叶子节点通常是 [名称, "", ID] 或 [名称, ID]
            if len(data) >= 2 and isinstance(data[0], str) and isinstance(data[-1], str):
                node_id = data[-1]
                name = data[0]
                if node_id.startswith(("chgn_", "new_")):
                    target_nodes.append((name, node_id))
            
            for item in data:
                find_target_ids(item)
        elif isinstance(data, dict):
            for v in data.values():
                find_target_ids(v)

    find_target_ids(all_data)
    # 去重
    target_nodes = list(set(target_nodes))
    print(f"[INFO] 提取到 {len(target_nodes)} 个目标概念/行业板块")

    stock_to_concepts = {}
    data_url_root = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
    
    for name, node_id in tqdm(target_nodes, desc="抓取各板块成分股"):
        params = {"page": "1", "num": "1000", "sort": "symbol", "asc": "1", "node": node_id}
        try:
            r = requests.get(data_url_root, params=params, headers=headers, timeout=10)
            stocks = r.json()
            if isinstance(stocks, list):
                for s in stocks:
                    raw_code = s.get('symbol') or s.get('code')
                    if not raw_code: continue
                    code = "".join(filter(str.isdigit, raw_code))[-6:]
                    if code not in stock_to_concepts:
                        stock_to_concepts[code] = []
                    if name not in stock_to_concepts[code]:
                        stock_to_concepts[code].append(name)
        except Exception:
            continue
        time.sleep(0.04)

    if stock_to_concepts:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(stock_to_concepts, f, ensure_ascii=False, indent=2)
            
    return stock_to_concepts

def update_csv():
    if not CSV_PATH.exists(): return
    df = pd.read_csv(CSV_PATH, dtype=str)
    mapping = get_sina_concepts()
    if not mapping: return

    concepts_col = []
    found_count = 0
    for _, row in df.iterrows():
        code = str(row['code']).zfill(6)
        concepts = mapping.get(code, [])
        if concepts:
            concepts_col.append(";".join(concepts))
            found_count += 1
        else:
            concepts_col.append("")
    
    df['concepts'] = concepts_col
    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    print(f"[OK] 同步完成，命中 {found_count}/{len(df)} 只股票")

if __name__ == "__main__":
    update_csv()
