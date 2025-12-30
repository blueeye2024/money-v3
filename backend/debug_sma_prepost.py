
import sys
import pandas as pd
import yfinance as yf
sys.path.append('/home/blue/blue/my_project/money/backend')
from analysis import calculate_sma

def check_ufo_prepost():
    print("Fetching UFO Data (Prepost=True)...")
    df_30 = yf.download("UFO", period="5d", interval="30m", prepost=True, progress=False)
    
    if df_30.empty:
        print("Data is empty!")
        return

    # Calculate SMA
    df_30['SMA10'] = calculate_sma(df_30['Close'], 10)
    df_30['SMA30'] = calculate_sma(df_30['Close'], 30)
    
    # Get last valid row
    # sometimes last row is NaN if just pushed?
    last = df_30.iloc[-1]
    
    print(f"Time: {df_30.index[-1]}")
    print(f"Price: {last['Close']}")
    print(f"SMA10: {last['SMA10']}")
    print(f"SMA30: {last['SMA30']}")
    
    if last['SMA10'] > last['SMA30']:
        print("Status: GOLD (SMA10 > SMA30)")
    else:
        print("Status: DEAD (SMA10 < SMA30)")
    
    print("\nRecent 10 Bars:")
    print(df_30.tail(10)[['Close', 'SMA10', 'SMA30']])

if __name__ == "__main__":
    check_ufo_prepost()
