
import sys
import os
import pandas as pd
import yfinance as yf
import pandas_ta as ta
from datetime import datetime
import pytz

# Add backend to path
sys.path.append('/home/blue/blue/my_project/money/backend')
from analysis import fetch_data

def check_soxs():
    print("Running SOXS Diagnostic...")
    
    # Fetch Data
    targets = ['SOXS']
    data_30m, data_5m, _, _, _ = fetch_data(targets, force=True)
    
    df_5 = data_5m.get('SOXS')
    if df_5 is None or df_5.empty:
        print("No SOXS Data found")
        return

    # Calculate Indicators
    df_5['ma10'] = df_5['Close'].rolling(window=10).mean()
    df_5['ma30'] = df_5['Close'].rolling(window=30).mean()
    
    # Last 5 rows
    print("\n--- Last 5 Rows (5m) ---")
    print(df_5[['Close', 'ma10', 'ma30']].tail(5))
    
    # Check Signal Logic
    row_curr = df_5.iloc[-1]
    row_prev = df_5.iloc[-2]
    
    ma10_c = row_curr['ma10']
    ma30_c = row_curr['ma30']
    ma10_p = row_prev['ma10']
    ma30_p = row_prev['ma30']
    
    print("\n--- Signal Check ---")
    print(f"Time (Latest): {df_5.index[-1]}")
    print(f"Prev: MA10={ma10_p:.4f}, MA30={ma30_p:.4f}")
    print(f"Curr: MA10={ma10_c:.4f}, MA30={ma30_c:.4f}")
    
    is_5m_gc = (ma10_p <= ma30_p) and (ma10_c > ma30_c)
    print(f"Is Golden Cross? {is_5m_gc}")
    
    if ma10_c > ma30_c:
        print("Current State: MA10 > MA30 (Bullish/Holding)")
    else:
        print("Current State: MA10 < MA30 (Bearish/Waiting)")

if __name__ == "__main__":
    check_soxs()
