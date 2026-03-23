import sqlite3
import pandas as pd

# The db is at /mnt/f/QIANQIAN/stock-fliter/get-data/data/stocks.db
# Table is daily_ohlcv (code, date, open, high, low, close, volume, amount, pctchg, turn)
conn = sqlite3.connect('/mnt/f/QIANQIAN/stock-fliter/get-data/data/stocks.db')
try:
    df = pd.read_sql_query("SELECT * FROM daily_ohlcv WHERE code LIKE '%300670%' ORDER BY date DESC LIMIT 30", conn)
    print("大烨智能 300670 近30日K线:")
    print(df[['date', 'close', 'pctchg', 'turn', 'volume']].head(10))
    # Quick analysis
    max_c = df['high'].max()
    min_c = df['low'].min()
    curr_c = df['close'].iloc[0]
    print(f"最近收盘价: {curr_c}")
    print(f"30日最高价: {max_c}")
    print(f"30日最低价: {min_c}")
    print(f"最近10日涨跌幅总和: {df['pctchg'].head(10).sum():.2f}%")
except Exception as e:
    print(f"Error querying db: {e}")
conn.close()
