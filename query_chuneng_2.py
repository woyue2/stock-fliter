import csv
import sqlite3
from collections import Counter

csv_path = '/mnt/f/QIANQIAN/stock-fliter/所有板块/所有股票行业分类；主营；概念 (1).csv'
db_path = '/mnt/f/QIANQIAN/stock-fliter/get-data/data/stocks.db'

chuneng_stocks = []
concept_counts = Counter()

with open(csv_path, 'r', encoding='gbk') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        if len(row) < 14: continue
        concepts = set(row[7].split(';'))
        if '储能' in concepts:
            code = row[0][:6] 
            name = row[1]
            try:
                mc = float(row[2]) / 1.0e8 # 亿
            except:
                mc = 9999
            ind = row[13]
            main_prod = row[6]
            chuneng_stocks.append({
                'code': code, 'name': name, 'mc': mc, 
                'concepts': concepts, 'ind': ind, 'main': main_prod
            })
            for c in concepts:
                if c != '储能':
                    concept_counts[c] += 1

top_concepts = [c for c, cnt in concept_counts.most_common(12) if c not in ('融资融券', '深股通', '沪股通', '富时罗素概念股', '标普道琼斯A股', '国企改革', '华为概念', '专精特新')]

conn = sqlite3.connect(db_path)
cur = conn.cursor()

def is_low_position(code):
    cur.execute('SELECT open, close, pctchg FROM daily_ohlcv WHERE code=? ORDER BY date DESC LIMIT 20', (code,))
    rows = cur.fetchall()
    if not rows: return False
    
    # 最近2日内是否涨停过
    for r in rows[:2]:
        if r[2] and r[2] > 9.0:
            return False
            
    closes = [r[1] for r in rows if r[1] is not None]
    if not closes: return False
    
    c_price = closes[0]
    c_max = max(closes)
    # 回挑超过 10%
    return c_price <= c_max * 0.90

candidates = []
for s in chuneng_stocks:
    if s['code'].startswith('9') or s['code'].startswith('8'): continue
    if 'ST' in s['name'] or '退' in s['name']: continue
    if s['mc'] < 50 and is_low_position(s['code']):
        candidates.append(s)

candidates.sort(key=lambda x: x['mc'])

for c in candidates[:6]:
    hot_concepts = set(top_concepts) & c['concepts']
    print(f"{c['name']} ({c['code']}) | 市值: {c['mc']:.1f}亿 | 行业: {c['ind']} | 共振: {', '.join(hot_concepts)}")
    print(f"   --主营: {c['main'][:50]}")

conn.close()
