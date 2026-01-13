import pymysql
import pandas as pd
import pandas_ta as ta
from datetime import datetime

DB_CONFIG = {
    "host": "114.108.180.228",
    "port": 3306,
    "user": "blueeye",
    "password": "blueeye0037!",
    "database": "mywork_01",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

def check_soxs():
    conn = pymysql.connect(**DB_CONFIG)
    with conn.cursor() as cursor:
        sql = """
        SELECT 
            CONCAT(candle_date, ' ', LPAD(hour, 2, '0'), ':', LPAD(minute, 2, '0'), ':00') as candle_time,
            close_price 
        FROM soxs_candle_data 
        ORDER BY candle_date DESC, hour DESC, minute DESC 
        LIMIT 100
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("No SOXS data")
        return

    # Convert to DataFrame
    df = pd.DataFrame(rows)
    df['Close'] = df['close_price'].astype(float)
    
    # Sort ASC
    df = df.iloc[::-1].reset_index(drop=True)
    
    # Calc MA
    df['SMA10'] = ta.sma(df['Close'], length=10)
    df['SMA30'] = ta.sma(df['Close'], length=30)
    
    print(f"\n[SOXS 5m Logic Check - Last 10 of {len(df)} candles]")
    tail = df.tail(10).copy()
    
    for i, row in tail.iterrows():
        # Find previous row
        if i == 0: continue
        prev = df.iloc[i-1]
        
        c10 = row['SMA10']
        c30 = row['SMA30']
        p10 = prev['SMA10']
        p30 = prev['SMA30']
        
        status = "-"
        if pd.notnull(p10) and pd.notnull(p30) and pd.notnull(c10) and pd.notnull(c30):
             if p10 <= p30 and c10 > c30:
                 status = "🔥 GOLDEN CROSS 🔥"
             elif p10 >= p30 and c10 < c30:
                 status = "💧 DEAD CROSS"
        
        diff = c10 - c30 if pd.notnull(c10) and pd.notnull(c30) else 0.0
        print(f"{row['candle_time']} | Close: {row['Close']:.2f} | MA10: {c10:.4f} | MA30: {c30:.4f} | Diff: {diff:.4f} | {status}")

if __name__ == "__main__":
    check_soxs()
