import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import pandas as pd
from analysis import fetch_data, stitch_kis_candles
from db import get_connection

def verify_gap_fill():
    print("🚀 Verifying Gap Filling Logic...")
    
    # 1. Fetch Data (Triggers Stitching)
    # Force=False relies on Cache, but we want to see if Fetch calls Stitch
    # Let's verify stitch_kis_candles directly or check cache after update.
    # We will call stitch_kis_candles manually on a dummy YF df to see result.
    
    dummy_yf = pd.DataFrame({
        'Open': [100, 101], 'High': [102, 103], 'Low': [99, 100], 'Close': [101, 102], 'Volume': [1000, 2000]
    }, index=pd.to_datetime([datetime.now() - timedelta(minutes=20), datetime.now() - timedelta(minutes=15)]))
    
    stitched = stitch_kis_candles("SOXL", dummy_yf, 5)
    
    print(f"📊 Original Rows: {len(dummy_yf)}, Stitched Rows: {len(stitched)}")
    if len(stitched) > len(dummy_yf):
        print("✅ Stitching Successful! (Rows increased)")
        print(stitched.tail(3))
    else:
        print("⚠️ Stitching returned same row count (Maybe Market Closed or No Data)")

    print("\n🚀 Verifying Database Snapshot...")
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT ticker, candle_time, gold_30m, score FROM market_indicators_snapshot WHERE ticker='SOXL'")
        row = cursor.fetchone()
        if row:
            print(f"✅ Snapshot Found for SOXL: {row}")
        else:
            print("❌ No Snapshot found for SOXL")
    conn.close()

if __name__ == "__main__":
    verify_gap_fill()
