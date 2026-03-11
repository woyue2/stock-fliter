import sqlite3
import pandas as pd
from datetime import datetime, timedelta

db_path = "/mnt/f/QIANQIAN/stock-fliter/get-data/data/stocks.db"
table_name = "daily_ohlcv"

def get_trading_days(start_date, end_date):
    """
    获取范围内的所有周一到周五的日期
    """
    days = []
    curr = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    while curr <= end:
        if curr.weekday() < 5:  # 0-4 is Mon-Fri
            days.append(curr.strftime('%Y-%m-%d'))
        curr += timedelta(days=1)
    return days

try:
    conn = sqlite3.connect(db_path)
    
    # 获取数据库中最近 30 天的所有日期
    print("--- 检查 SQLite 中最近 30 个工作日的记录数 ---")
    df_dates = pd.read_sql_query(f"""
        SELECT date, COUNT(*) as stock_count 
        FROM {table_name} 
        GROUP BY date 
        ORDER BY date DESC 
        LIMIT 30
    """, conn)
    
    if df_dates.empty:
        print("数据库中无记录。")
    else:
        print(df_dates)
        
        # 检查日期连续性
        max_date = df_dates['date'].max()
        min_date = df_dates['date'].min()
        expected_days = get_trading_days(min_date, max_date)
        
        actual_days = set(df_dates['date'].tolist())
        missing_days = [d for d in expected_days if d not in actual_days]
        
        print(f"\n检查范围: {min_date} 到 {max_date}")
        if missing_days:
            print(f"⚠️ 发现缺失的工作日: {missing_days}")
        else:
            print("✅ 在查询范围内，工作日（周一至周五）在数据库中都有记录。")

    conn.close()
except Exception as e:
    print(f"检查失败: {e}")
