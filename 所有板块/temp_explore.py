import pandas as pd
import sqlite3
import json
import re

csv_path = '/mnt/f/QIANQIAN/stock-fliter/所有板块/所有股票行业分类；主营；概念 (1).csv'

df = pd.read_csv(csv_path, encoding='gb18030', header=None, index_col=False)


def find_stock(code):
    for i, row in df.iterrows():
        if code in str(row[0]):
            return row
    return None

hua = find_stock('600396')
if hua is not None:
    concepts_raw = str(hua[6])
    industry = str(hua[9])
    main_business = str(hua[5])
    print(f"华电辽能 概念: {concepts_raw}")
    print(f"华电辽能 行业: {industry}")
    print(f"华电辽能 主营: {main_business}")
else:
    print("Not found")

# We want to find common concepts for '绿电', '氢能', '央企' in the CSV.
def search_concepts(*kws):
    matches = df[df[6].astype(str).str.contains('|'.join(kws), regex=True, na=False)]
    concept_counts = {}
    for idx, row in matches.iterrows():
        craw = str(row[6])
        for c in craw.split(';'):
            c = c.strip()
            if c:
                concept_counts[c] = concept_counts.get(c, 0) + 1
    sorted_c = sorted(concept_counts.items(), key=lambda x: -x[1])
    return sorted_c[:15], matches

top_c, matches = search_concepts('绿电', '氢能')
print("Top concepts connected to 绿电/氢能:")
for k, v in top_c:
    print(k, v)

# Let's filter low market cap stocks from these matches
# df[2] appears to be total share or market cap? We can check the columns.
print("\nSample match:")
print(matches.head(1).values)

