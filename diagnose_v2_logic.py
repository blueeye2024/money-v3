
import sys
import os
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import pytz
from datetime import datetime

# Add backend to path
sys.path.append('/home/blue/blue/my_project/money/backend')
from analysis import fetch_data, get_v2_buy_status

def diagnose_soxs_v2():
    print("Running V2 Logic Diagnostic for SOXS...")
    
    # 1. Fetch Data
    targets = ['SOXS']
    data_30m, data_5m, data_1d, _, _ = fetch_data(targets, force=True)
    
    df_5 = data_5m['SOXS']
    df_30 = data_30m['SOXS']
    d1 = data_1d['SOXS']
    
    # Clean/Resample (Mirroring analysis.py)
    if not isinstance(df_5.index, pd.DatetimeIndex): df_5.index = pd.to_datetime(df_5.index)
    if not isinstance(df_30.index, pd.DatetimeIndex): df_30.index = pd.to_datetime(df_30.index)
    
    df_5 = df_5.resample('5min').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
    df_30 = df_30.resample('30min').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
    
    # 2. Indicators
    # 30m
    df_30['ma10'] = df_30['Close'].rolling(window=10).mean()
    df_30['ma30'] = df_30['Close'].rolling(window=30).mean()
    df_30['box_high'] = df_30['High'].rolling(window=20).max().shift(1)
    df_30['vol_ma5'] = df_30['Volume'].rolling(window=5).mean()
    
    # 1D
    prev_close = float(d1['Close'].iloc[-2]) if len(d1) >= 2 else float(d1['Close'].iloc[-1])
    
    curr_price = float(df_5['Close'].iloc[-1])
    # Patch KIS Price for Display Logic similarity
    try:
        from kis_api import kis_client
        kis_p = kis_client.get_price(targets[0])
        if kis_p: curr_price = float(kis_p['price'])
    except: pass

    # Find where Box High comes from
    # Rolling max of 'High' window=20, shifted 1.
    # We want to find the IDxmax in the last 20 periods of the shifted series?
    # No, just look at the last 21 candles of High.
    last_20_highs = df_30['High'].iloc[-21:-1]
    box_high_val = last_20_highs.max()
    box_high_idx = last_20_highs.idxmax()
    
    print("\n--- DATA VALUES ---")
    print(f"Current Price (KIS): {curr_price}")
    print(f"Box High Source: {box_high_val} at {box_high_idx}")
    print(f"Prev Close (1D): {prev_close}")
    print(f"Box High (20-30m): {box_high}")
    print(f"Vol 30m: {curr_vol_30}")
    print(f"Vol MA5 (30m): {curr_vol_ma_30}")
    print(f"MA10 (30m): {ma10_30:.4f} (Prev: {prev_ma10_30:.4f})")
    print(f"MA30 (30m): {ma30_30:.4f} (Prev: {prev_ma30_30:.4f})")
    
    print("\n--- LOGIC CHECK ---")
    
    # Sig 2 Check
    cond_box = curr_price > box_high
    cond_2pct = (prev_close > 0) and (curr_price > prev_close * 1.02)
    cond_vol = (curr_vol_ma_30 > 0) and (curr_vol_30 > curr_vol_ma_30 * 1.5)
    
    print(f"Sig 2 - Box ({box_high}): {cond_box}")
    print(f"Sig 2 - +2% (Target {prev_close*1.02:.2f}): {cond_2pct}")
    print(f"Sig 2 - Vol Surge (Target {curr_vol_ma_30*1.5:.0f}): {cond_vol}")
    print(f"Final Sig 2: {cond_box and cond_2pct and cond_vol}")
    
    # Sig 3 Check (Cross)
    is_30m_gc = (prev_ma10_30 <= prev_ma30_30) and (ma10_30 > ma30_30)
    
    # Catch-up for Sig 3?
    is_30m_trend = (ma10_30 > ma30_30)
    
    print(f"Sig 3 - GC Cross: {is_30m_gc}")
    print(f"Sig 3 - Trend Up (MA10 > MA30): {is_30m_trend}")
    
    print("\n--- DB STATUS ---")
    status = get_v2_buy_status('SOXS')
    print(status)

if __name__ == "__main__":
    diagnose_soxs_v2()
