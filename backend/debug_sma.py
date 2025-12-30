
import sys
import pandas as pd
import yfinance as yf
sys.path.append('/home/blue/blue/my_project/money/backend')
from analysis import calculate_sma, calculate_rsi

def check_ufo():
    print("Fetching UFO Data...")
    df_30 = yf.download("UFO", period="5d", interval="30m", progress=False)
    
    # Calculate SMA
    df_30['SMA10'] = calculate_sma(df_30['Close'], 10)
    df_30['SMA30'] = calculate_sma(df_30['Close'], 30)
    
    last_10 = df_30['SMA10'].iloc[-1]
    last_30 = df_30['SMA30'].iloc[-1]
    price = df_30['Close'].iloc[-1]
    last_time = df_30.index[-1]
    
    print(f"Time: {last_time}")
    print(f"Price: {price}")
    print(f"SMA10: {last_10}")
    print(f"SMA30: {last_30}")
    
    if last_10 > last_30:
        print("Status: GOLD (SMA10 > SMA30)")
    else:
        print("Status: DEAD (SMA10 < SMA30)")
        
    print("\nRecent Data:")
    print(df_30.tail(5)[['Close', 'SMA10', 'SMA30']])

if __name__ == "__main__":
    check_ufo()
