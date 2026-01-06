
from db import get_connection
import pandas as pd

def check_db(ticker):
    conn = get_connection()
    cursor = conn.cursor()
    
    print(f"--- Checking {ticker} 30m ---")
    cursor.execute(f"SELECT candle_time, close_price, source, updated_at FROM market_candles WHERE ticker='{ticker}' AND timeframe='30m' ORDER BY candle_time DESC LIMIT 10")
    rows = cursor.fetchall()
    for r in rows:
        print(r)
        
    print(f"\n--- Checking {ticker} 5m ---")
    cursor.execute(f"SELECT candle_time, close_price, source, updated_at FROM market_candles WHERE ticker='{ticker}' AND timeframe='5m' ORDER BY candle_time DESC LIMIT 10")
    rows = cursor.fetchall()
    for r in rows:
        print(r)

check_db("SOXL")
