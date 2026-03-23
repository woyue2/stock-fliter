import sqlite3
import pandas as pd

# Query stocks.db for several candidate low-cap stocks mentioned/suspected in 0320 analysis
conn = sqlite3.connect('/mnt/f/QIANQIAN/stock-fliter/get-data/data/stocks.db')

candidates = {
    '300670': '大烨智能',
    '001382': '新亚电缆',
    '300635': '中达安',
    '605389': '长龄液压',
    '000862': '银星能源',  # already 首板
    '002150': '正泰电源',  # already 首板
    '603778': '国晟科技',  # already 首板
    '301658': '首航新能',  # already 首板
}

for code, name in candidates.items():
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
