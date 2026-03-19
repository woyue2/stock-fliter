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

print('--- 横向伴生概念 TOP 5 ---')
top_concepts = [c for c, cnt in concept_counts.most_common(12) if c not in ('融资融券', '深股通', '沪股通', '富时罗素概念股', '标普道琼斯A股', '国企改革', '华为概念')]
for c in top_concepts[:5]:
    print(c)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

def is_low_position(code):
    cur.execute('SELECT open, close, pctchg FROM daily_ohlcv WHERE code=? ORDER BY date DESC LIMIT 20', (code,))
    rows = cur.fetchall()
    if not rows: return False
    
    # 过滤两天内涨停的（不是盲点）
    recent_2 = rows[:2]
    for r in recent_2:
        if r[2] and r[2] > 9.0:
            return False
            
    closes = [r[1] for r in rows if r[1] is not None]
    if not closes: return False
    
    c_price = closes[0]
    c_max = max(closes)
    
    # 距离高点回撤超过15%，说明在低位，或者处于极度缩量状态
    # 简化：只找在低位的票
    return c_price <= c_max * 0.90

candidates = [s for s in chuneng_stocks if s['mc'] < 40 and is_low_position(s['code'])]

print(f'\n--- 纵向产业链分布概览 (针对低位小盘候选池) ---')
ind_counts = Counter([s['ind'] for s in candidates])
for ind, cnt in ind_counts.most_common(3):
    print(f"{ind}: {cnt}只")

candidates.sort(key=lambda x: x['mc'])

print('\n--- 低位埋伏候选 (流通市值 < 40亿，近20日高点回调 > 10%，近2日未涨停) ---')
for c in candidates[:8]:
    # 找出它的其它热点概念
    hot_concepts = set(top_concepts) & c['concepts']
    print(f"{c['name']} ({c['code']}) | 市值: {c['mc']:.1f}亿 \n  >> 行业: {c['ind']} \n  >> 共振: {', '.join(hot_concepts)} \n  >> 主营: {c['main'][:40]}")

conn.close()
