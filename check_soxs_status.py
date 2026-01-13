from backend.db import get_connection
import pandas as pd
import pandas_ta as ta

def check_soxs():
    conn = get_connection()
    # 5분봉 조회
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
    
    # Check Gold Cross in last few candles
    for i in range(len(df)-1, len(df)-4, -1):
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        if prev['SMA10'] <= prev['SMA30'] and curr['SMA10'] > curr['SMA30']:
            print(f"!!! GOLDEN CROSS FOUND at {curr['candle_time']} !!!")
            return
            
    print("No Golden Cross found in recent 3 candles")

if __name__ == "__main__":
    check_soxs()
