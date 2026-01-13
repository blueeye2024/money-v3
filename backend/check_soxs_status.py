import sys
import os
# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import get_connection
import pandas as pd
import pandas_ta as ta

def check_soxs():
    conn = get_connection()
    # 5m data
    sql = "SELECT candle_time, close_price as Close FROM soxs_candle_data WHERE timeframe='5m' ORDER BY candle_time DESC LIMIT 50"
    df = pd.read_sql(sql, conn)
    conn.close()
    
    if df.empty:
        print("No SOXS 5m data found")
        return

    df = df.iloc[::-1].reset_index(drop=True)
    df['SMA10'] = ta.sma(df['Close'], length=10)
    df['SMA30'] = ta.sma(df['Close'], length=30)
    
    print("\n[SOXS 5m Review]")
    print(df[['candle_time', 'Close', 'SMA10', 'SMA30']].tail(5))
    
    # Check Gold Cross
    print("\n[Checking Signal Logic]")
    for i in range(len(df)-1, len(df)-5, -1):
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        
        c10 = curr['SMA10']
        c30 = curr['SMA30']
        p10 = prev['SMA10']
        p30 = prev['SMA30']
        
        is_gold = p10 <= p30 and c10 > c30
        print(f"Time: {curr['candle_time']} | Prev: {p10:.2f}/{p30:.2f} | Curr: {c10:.2f}/{c30:.2f} | GC: {is_gold}")

if __name__ == "__main__":
    check_soxs()
