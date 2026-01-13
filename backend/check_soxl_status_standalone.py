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

def check_soxl():
    print(f"[{datetime.now()}] Connecting to DB...")
    conn = pymysql.connect(**DB_CONFIG)
    with conn.cursor() as cursor:
        sql = """
        SELECT 
            CONCAT(candle_date, ' ', LPAD(hour, 2, '0'), ':', LPAD(minute, 2, '0'), ':00') as candle_time,
            close_price 
        FROM soxl_candle_data 
        ORDER BY candle_date DESC, hour DESC, minute DESC 
        LIMIT 100
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("No SOXL data")
        return

    df = pd.DataFrame(rows)
    # Use 'close_price' column from dict
    df['Close'] = df['close_price'].astype(float)
    
    # Sort ASC
    df = df.iloc[::-1].reset_index(drop=True)
    
    df['SMA10'] = ta.sma(df['Close'], length=10)
    df['SMA30'] = ta.sma(df['Close'], length=30)
    
    print("\n[SOXL 5m Review (Last 5)]")
    print(df[['candle_time', 'Close', 'SMA10', 'SMA30']].tail(5))

    # Check Gold
    print("\n[Checking Signal Logic]")
    for i in range(len(df)-1, len(df)-10, -1):
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        c10 = curr['SMA10']
        c30 = curr['SMA30']
        p10 = prev['SMA10']
        p30 = prev['SMA30']
        
        if pd.notnull(p10) and p10 <= p30 and c10 > c30:
             print(f"🔥 SOXL GOLDEN CROSS at {curr['candle_time']}! ({c10:.2f} > {c30:.2f})")
             return
    
    print("No recent SOXL Golden Cross found.")

if __name__ == "__main__":
    check_soxl()
