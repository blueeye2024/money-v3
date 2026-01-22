import sys
import os
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timezone
import pytz

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.append(os.path.dirname(__file__))

from backend.analysis import fetch_data, get_cross_history

def debug_cross_history():
    tickers = ['SOXL']
    print(f"🔍 Debugging Cross History for {tickers}...")
    
    # 1. Fetch Data
    data_30m, data_5m, _, _, _ = fetch_data(tickers, force=True)
    
    t = 'SOXL'
    df_30 = data_30m[t]
    df_5 = data_5m[t]
    
    print(f"\n[Data Stats]")
    print(f"  30m Rows: {len(df_30)}")
    print(f"  5m Rows: {len(df_5)}")
    
    # 2. Run Cross History
    print(f"\n[Running get_cross_history]")
    history = get_cross_history(df_30, df_5)
    
    print("\n[Result]")
    print(os.linesep.join([f"  {k}: {v}" for k, v in history.items()]))
    
    if not history['gold_30m'] and not history['gold_5m'] and not history['dead_5m']:
        print("\n⚠️ No crosses detected. Checking recent SMA values...")
        
        # Check last few rows of 30m
        if not df_30.empty:
            d30 = df_30.copy()
            d30['SMA10'] = ta.sma(d30['Close'], length=10)
            d30['SMA30'] = ta.sma(d30['Close'], length=30)
            print("\n  [Recent 30m SMAs]")
            print(d30[['Close', 'SMA10', 'SMA30']].tail(5))
            
        # Check last few rows of 5m
        if not df_5.empty:
            d5 = df_5.copy()
            d5['SMA10'] = ta.sma(d5['Close'], length=10)
            d5['SMA30'] = ta.sma(d5['Close'], length=30)
            print("\n  [Recent 5m SMAs]")
            print(d5[['Close', 'SMA10', 'SMA30']].tail(5))

if __name__ == "__main__":
    debug_cross_history()
