import sys
import os
import pandas as pd
import pandas_ta as ta
import pytz
from datetime import datetime

# Add path for backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from analysis import fetch_data
    
    print("Fetching Data (Force Refresh)...")
    # Force fetch to ensure we have latest
    d30, d5, _, _, _ = fetch_data(tickers=['SOXL'], force=True, override_period='5d')
    
    ticker = 'SOXL'
    
    # Check 30m
    if ticker in d30 and not d30[ticker].empty:
        df = d30[ticker].copy()
        df['SMA10'] = ta.sma(df['Close'], 10)
        df['SMA30'] = ta.sma(df['Close'], 30)
        
        print("\n=== SOXL 30m Moving Averages (Last 5 Candles) ===")
        tail = df.tail(5)
        for idx, row in tail.iterrows():
            # Convert index to KST
            dt = idx
            if dt.tzinfo is None:
                dt = pytz.timezone('America/New_York').localize(dt)
            dt_kst = dt.astimezone(pytz.timezone('Asia/Seoul'))
            
            s10 = row['SMA10']
            s30 = row['SMA30']
            state = "Bull (10>30)" if s10 > s30 else "Bear (10<30)"
            print(f"[{dt_kst.strftime('%m-%d %H:%M')}] Close: {row['Close']:.2f} | SMA10: {s10:.2f} | SMA30: {s30:.2f} -> {state}")

    # Check 5m
    if ticker in d5 and not d5[ticker].empty:
        df = d5[ticker].copy()
        df['SMA10'] = ta.sma(df['Close'], 10)
        df['SMA30'] = ta.sma(df['Close'], 30)
        
        print("\n=== SOXL 5m Moving Averages (Last 10 Candles) ===")
        tail = df.tail(10)
        for idx, row in tail.iterrows():
             # Convert index to KST
            dt = idx
            if dt.tzinfo is None:
                dt = pytz.timezone('America/New_York').localize(dt)
            dt_kst = dt.astimezone(pytz.timezone('Asia/Seoul'))
            
            s10 = row['SMA10']
            s30 = row['SMA30']
            state = "Bull (10>30)" if s10 > s30 else "Bear (10<30)"
            print(f"[{dt_kst.strftime('%m-%d %H:%M')}] Close: {row['Close']:.2f} | SMA10: {s10:.2f} | SMA30: {s30:.2f} -> {state}")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
