import pandas as pd
import sqlite3

csv_path = '/mnt/f/QIANQIAN/stock-fliter/所有板块/所有股票行业分类；主营；概念 (1).csv'
df = pd.read_csv(csv_path, encoding='gb18030', header=None, index_col=False)

# Find stocks with 绿色电力 or 氢能源 that have small market cap
def find_low_cap_stocks(kws, max_cap=5000000000):
    # df[2] is likely total market cap or circulating market cap. Let's assume df[3] is circulating float?
    # Let's just use string contains and print a few to see
    matches = df[df[6].astype(str).str.contains('|'.join(kws), regex=True, na=False)]
    res = []
    for _, row in matches.iterrows():
        code = str(row[0]).split('.')[0]
        name = str(row[1])
        cap = float(row[2]) if str(row[2]).replace('.','',1).isdigit() else 0
        concepts = str(row[6])
        industry = str(row[13])
        if cap < max_cap and cap > 0:
            res.append((code, name, cap/100000000, concepts, industry))
    
    # Sort by cap
    res.sort(key=lambda x: x[2])
    return res[:5]

print("低位绿电/氢能:")
for s in find_low_cap_stocks(['绿色电力', '氢能源', '光伏发电']):
    print(s)
