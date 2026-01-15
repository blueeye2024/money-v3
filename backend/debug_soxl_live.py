
import sys
import os
sys.path.append('/home/blue/blue/my_project/money/backend')

import pandas as pd
import pandas_ta as ta
import yfinance as yf
from datetime import datetime, timedelta

def check_soxl_live():
    ticker = "SOXL"
    print(f"[{datetime.now()}] Checking {ticker} Live Signals via YFinance...")
    
    # [FIX] Use group_by='ticker' to match analysis.py behavior
    df = yf.download(ticker, period="5d", interval="5m", prepost=True, progress=False, group_by='ticker')
    
    if df.empty:
        print("No data fetched.")
        return

    # Check Columns (MultiIndex handling)
    # With group_by='ticker', Level 0 should be Ticker
    if isinstance(df.columns, pd.MultiIndex):
        # Flatten simple case if one ticker
        # If columns are (SOXL, Close), xs('SOXL', level=0, axis=1) -> columns (Close...)
        try:
             df = df.xs(ticker, axis=1, level=0)
        except Exception as e:
             print(f"XS Error: {e}. Columns: {df.columns}")
             # Try flattening if single ticker but messed up levels
             if len(df.columns.levels) == 2:
                  df.columns = df.columns.droplevel(0)
    
    print(f"Data Rows: {len(df)}")
    print("Columns:", df.columns)

    # Ensure Close is valid
    if 'Close' not in df.columns:
        print("Close column missing:", df.columns)
        return
    
    print(f"Data Rows: {len(df)}")
    print("Columns:", df.columns)
    print("Head:", df['Close'].head())
        
    # Calculate Indicators
    try:
        df['SMA10'] = ta.sma(df['Close'], length=10)
        df['SMA30'] = ta.sma(df['Close'], length=30)
        print("SMA10 Sample:", df['SMA10'].tail())
    except Exception as e:
        print(f"TA Error: {e}")
    
    print("\n[Last 10 Candles]")
    tail = df.tail(10)
    for idx, row in tail.iterrows():
        t_str = idx.strftime("%m-%d %H:%M")
        
        def safe_float(val):
            try:
                if hasattr(val, 'iloc'): val = val.iloc[0]
                return float(val) if pd.notnull(val) else 0.0
            except: return 0.0
            
        c = safe_float(row['Close'])
        s10 = safe_float(row['SMA10'])
        s30 = safe_float(row['SMA30'])
        
        print(f"{t_str} | Close: {c:.2f} | SMA10: {s10:.2f} | SMA30: {s30:.2f}")

    # Explicit Cross Check on recent data
    print("\n[Cross Check Analysis]")
    found = False
    for i in range(len(df)-1, len(df)-20, -1):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        c10 = safe_float(curr['SMA10'])
        c30 = safe_float(curr['SMA30'])
        p10 = safe_float(prev['SMA10'])
        p30 = safe_float(prev['SMA30'])
        
        if c10 == 0 or p10 == 0: continue
        
        if p10 <= p30 and c10 > c30:
            print(f"🔥 GOLDEN CROSS CANDIDATE at {df.index[i]} (Prev: {p10:.2f}<={p30:.2f} -> Curr: {c10:.2f}>{c30:.2f})")
            found = True
            
    if not found:
        print("No Golden Cross found in last 20 candles.")

if __name__ == "__main__":
    check_soxl_live()
