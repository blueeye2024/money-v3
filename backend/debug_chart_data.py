import sys
import os
import json
from datetime import datetime

# Add path
sys.path.append(os.getcwd())

from db import get_mini_chart_data, get_connection

def debug_chart():
    ticker = 'SOXL'
    print(f"--- Debugging Chart Data for {ticker} ---")
    
    # 1. Check DB Raw Data (Last 10 rows)
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(f"SELECT * FROM {ticker.lower()}_candle_data ORDER BY candle_date DESC, hour DESC, minute DESC LIMIT 10")
        rows = cur.fetchall()
        print("\n[Raw DB Data (Last 10)]")
        for r in rows:
            print(f"Date={r['candle_date']}, Time={r['hour']:02d}:{r['minute']:02d}, Close={r['close_price']}, Source={r['source']}")
            
    # 2. Check get_mini_chart_data Output
    data = get_mini_chart_data(ticker)
    candles_5m = data['candles_5m']
    
    print(f"\n[API Output (candles_5m) (Last 10 of {len(candles_5m)})]")
    # candles_5m is ordered oldest to newest (reversed in db.py)
    # print last 10
    for c in candles_5m[-10:]:
        print(c)

    # 3. Check for Gap
    if len(candles_5m) >= 2:
        last = candles_5m[-1]
        print(f"\nLast Candle Time: {last['time']}")
        # Current time check is manual

if __name__ == "__main__":
    debug_chart()
