import sqlite3
import pandas as pd

def get_data():
    db_path = "../../get-data/data/stocks.db"
    codes = ['002350.SZ', '600578.SH', '002893.SZ', '601016.SH', '300670.SZ']
    
    conn = sqlite3.connect(db_path)
    
    # Get last 20 days
    query = f"""
    SELECT code, date, open, high, low, close, volume, pctchg, turn
    FROM daily_ohlcv
    WHERE code IN ({','.join(['?' for _ in codes])})
    ORDER BY date DESC
    LIMIT 100
    """
    
    df = pd.read_sql_query(query, conn, params=codes)
    conn.close()
    
    # Process each stock
    for code in codes:
        sdf = df[df['code'] == code].sort_values('date')
        if sdf.empty:
            print(f"No data for {code}")
            continue
            
        print(f"\n--- {code} ---")
        # Latest data
        latest = sdf.iloc[-1]
        prev = sdf.iloc[-2] if len(sdf) > 1 else latest
        
        avg_vol_5 = sdf['volume'].tail(5).mean()
        avg_vol_20 = sdf['volume'].mean()
        
        vol_ratio = latest['volume'] / avg_vol_5 if avg_vol_5 > 0 else 1
        
        print(f"Date: {latest['date']} | Close: {latest['close']} | PctChg: {latest['pctchg']}% | Turn: {latest['turn']}%")
        print(f"Volume Ratio (vs 5D Avg): {vol_ratio:.2f}")
        
        # Determine Signal
        signal = "Stable"
        if latest['pctchg'] > 0 and latest['volume'] > prev['volume'] * 1.5:
            signal = "Right-side Breakout/Volume up"
        elif latest['pctchg'] < 0 and latest['volume'] < avg_vol_5 * 0.7:
            signal = "Left-side Shrinking/Bottoming"
        elif latest['close'] > sdf['close'].tail(5).max() * 0.98:
            signal = "Strong/Near Resistance"
            
        print(f"Signal: {signal}")
        
        # Show last 5 days
        print(sdf.tail(5)[['date', 'close', 'pctchg', 'volume', 'turn']].to_string(index=False))

if __name__ == "__main__":
    get_data()
