import sys
import os
import yfinance as yf
import pandas as pd
import numpy as np

# Mock DB connection
from db import get_connection

def calculate_sma(series, window):
    return series.rolling(window=window).mean()

def check_sell_logic():
    ticker = 'SOXL'
    print(f"checking {ticker}...")
    
    # Fetch Data just like populate_soxl or analysis
    df = yf.download(ticker, interval="5m", period="1d", progress=False)
    print(f"Columns: {df.columns}")
    if isinstance(df.columns, pd.MultiIndex):
        if ticker in df.columns.levels[0]:
            df = df.xs(ticker, axis=1, level=0)
    
    # Print last few rows to debug data
    print(df.tail())
    
    # Calculate indicators
    df['SMA10'] = calculate_sma(df['Close'], 10)
    
    if len(df) < 10:
        print("Not enough data")
        return

    # Get last row
    last_row = df.iloc[-1]
    curr_price = float(last_row['Close'])
    curr_ma10 = float(last_row['SMA10'])
    
    # Calculate LRS
    y = df['Close'].tail(10).values
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    lrs_val = slope
    
    print(f"Price: {curr_price}")
    print(f"MA10: {curr_ma10}")
    print(f"LRS: {lrs_val}")
    
    is_sig2_met = (lrs_val < 0)
    print(f"LRS < 0 condition: {is_sig2_met}")
    
    if is_sig2_met and curr_price >= curr_ma10:
        print("Strength Filter: Price >= MA10. Signal REJECTED.")
        is_sig2_met = False
    else:
        print("Strength Filter: Price < MA10. Signal ACCEPTED.")
        
    print(f"Final Step 2 Result: {is_sig2_met}")

if __name__ == "__main__":
    check_sell_logic()
