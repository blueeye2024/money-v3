
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import pytz
from datetime import datetime

def verify_signal():
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)

    print("Fetching SOXL 30m data (1mo, prepost=True)...")
    df = yf.download("SOXL", period="1mo", interval="30m", prepost=True, progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    # Timezone conversion
    ny_tz = pytz.timezone('America/New_York')
    if df.index.tz is None:
        df.index = df.index.tz_localize('America/New_York')
    else:
        df.index = df.index.tz_convert(ny_tz)

    # Clean
    df = df.dropna(subset=['Close'])

    # Calc Indicators
    df['SMA10'] = ta.sma(df['Close'], length=10)
    df['SMA30'] = ta.sma(df['Close'], length=30)
    
    print("\n--- Searching for Recent Golden Cross (SMA10 > SMA30) ---")
    
    found = False
    for i in range(len(df)-1, 1, -1):
        c_10 = df['SMA10'].iloc[i]
        c_30 = df['SMA30'].iloc[i]
        p_10 = df['SMA10'].iloc[i-1]
        p_30 = df['SMA30'].iloc[i-1]
        
        # Check Golden Cross
        if p_10 <= p_30 and c_10 > c_30:
             idx_time = df.index[i]
             print(f"🎯 FOUND Golden Cross at: {idx_time} (NY)")
             print(f"   Price: {df['Close'].iloc[i]:.2f}")
             print(f"   SMA10: {c_10:.2f}, SMA30: {c_30:.2f}")
             print(f"   Prev  : {df.index[i-1]} (SMA10: {p_10:.2f}, SMA30: {p_30:.2f})")
             found = True
             break
             
    if not found:
        print("No Golden Cross found in loaded data.")

    # Specific check for 2026-01-06 00:00
    print("\n--- Checking Data around 2026-01-06 00:00 (NY Time) ---")
    # Correctly define NY time
    target_start = ny_tz.localize(datetime(2026, 1, 5, 23, 0, 0)) # 11 PM Prev Day
    target_end = ny_tz.localize(datetime(2026, 1, 6, 6, 0, 0))   # 6 AM Target Day
    
    subset = df[(df.index >= target_start) & (df.index <= target_end)]
    if not subset.empty:
        print(subset[['Close', 'SMA10', 'SMA30']])
    else:
        print("No data found between Jan 5 23:00 and Jan 6 06:00 NY")

if __name__ == "__main__":
    verify_signal()
