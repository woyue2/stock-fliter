import sqlite3
import pandas as pd

conn = sqlite3.connect('/mnt/f/QIANQIAN/stock-fliter/get-data/data/stocks.db')

# Further candidates - stocks in 绿电/储能/光伏 space that might be low-position
# Based on the concepts search results from CSV, let's check a few more
more_candidates = {
    '600032': '浙江新能',
    '603018': '中设股份', 
    '000875': '吉电股份',
    '600979': '广安爱众',
    '601016': '节能风电',
    '002015': '协鑫集成',
}

for code, name in more_candidates.items():
    try:
        df = pd.read_sql_query(
            f"SELECT date, close, pctchg, turn, volume FROM daily_ohlcv WHERE code LIKE '%{code}%' ORDER BY date DESC LIMIT 10",
            conn
        )
        if df.empty:
            print(f"{name}({code}): 无数据")
            continue
        curr = df['close'].iloc[0]
        max_c = df['close'].max()
        min_c = df['close'].min()
        pct_sum = df['pctchg'].head(5).sum()
        turn_recent = df['turn'].iloc[0]
        print(f"[{code}] {name}: 收盘={curr:.2f} | 5日累计涨跌={pct_sum:.2f}% | 换手={turn_recent:.2f}% | 10日高/低={max_c:.2f}/{min_c:.2f}")
    except Exception as e:
        print(f"{name}({code}): 查询错误 {e}")

conn.close()
