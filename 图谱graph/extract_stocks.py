import sqlite3
import json

db_path = '../get-data/data/stocks.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT code FROM stock_info")
rows = cursor.fetchall()

# Clean codes (assuming they might have prefixes/suffixes)
codes = [row[0] for row in rows]

with open('a_stock.txt', 'w', encoding='utf-8') as f:
    json.dump(codes, f, ensure_ascii=False)

print(f"Extracted {len(codes)} stocks to a_stock.txt")
conn.close()
