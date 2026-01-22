
import sys
import os
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime
import pytz
import traceback

# Add backend to path to allow importing kis_api_v2
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from backend.analysis import fetch_data, calculate_lrs
except ImportError:
    # If calculate_lrs is not exported or fetch_data needs args
    pass

try:
    from kis_api_v2 import kis_client
except ImportError:
    print("⚠️ Could not import kis_api_v2. Make sure you are in the project root.")
    kis_client = None

def simple_lrs(series, length=10):
    try:
        if len(series) < length: return -999
        y = series.tail(length).values
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        return slope
    except:
        return -999

def stitch_kis_candles(ticker, yf_df, interval_min):
    """
    Fetches missing candles from KIS API and appends/overwrites YFinance DF.
    """
    if not kis_client: return yf_df
    
    try:
        # Fetch recent candles from KIS
        candles = kis_client.get_minute_candles(ticker, interval_min=interval_min)
        if not candles: 
            print(f"    ⚠️ Stitch: No KIS candles for {ticker} (Interval {interval_min}m)")
            return yf_df
        
        print(f"    🧵 Stitching {len(candles)} KIS candles ({interval_min}m)...")
        
        # Convert to DataFrame
        new_data = []
        kst = pytz.timezone('Asia/Seoul')
        utc = pytz.timezone('UTC')
        
        for c in candles:
            # Parse KST Time (kymd + khms)
            dt_str = c['kymd'] + c['khms']
            dt_kst = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
            dt_kst = kst.localize(dt_kst)
            
            # Convert to YFinance Timezone (usually UTC)
            if not yf_df.empty and yf_df.index.tz:
                 dt_target = dt_kst.astimezone(yf_df.index.tz)
            else:
                 dt_target = dt_kst.astimezone(utc)
            
            new_data.append({
                'Datetime': dt_target,
                'Open': float(c['open']),
                'High': float(c['high']),
                'Low': float(c['low']),
                'Close': float(c['last']),
                'Volume': int(c['evol']) 
            })
            
        kis_df = pd.DataFrame(new_data)
        kis_df.set_index('Datetime', inplace=True)
        
        # Combine and Deduplicate
        # We prioritize KIS data for overlapping timestamps
        combined = pd.concat([yf_df, kis_df])
        combined = combined[~combined.index.duplicated(keep='last')]
        combined.sort_index(inplace=True)
        
        return combined
        
    except Exception as e:
        print(f"    ⚠️ Stitch Error: {e}")
        return yf_df

def verify_soxl():
    print("🔍 SOXL Signal Verification Start (Data Source: YF + KIS Patch)...")
    
    # 1. Fetch Data
    # We can rely on pandas_ta/yfinance or just use internal logic if possible.
    # To match system exactly, we should try to use the same fetch method.
    # Let's mock the analysis environment or just recreate the fetch.
    
    import yfinance as yf
    
    print("⏳ Fetching SOXL data (YFinance)...")
    ticker = "SOXL"
    
    # Fetch 5m
    df_5 = yf.download(ticker, period="5d", interval="5m", progress=False)
    if df_5.empty:
        print("❌ Failed to fetch 5m data")
        return
    
    # Flatten MultiIndex columns if present (yfinance v0.2.x+ style)
    if isinstance(df_5.columns, pd.MultiIndex):
        df_5.columns = [col[0] for col in df_5.columns]

    # Fetch 30m
    df_30 = yf.download(ticker, period="5d", interval="30m", progress=False)
    if df_30.empty:
        print("❌ Failed to fetch 30m data")
        return

    if isinstance(df_30.columns, pd.MultiIndex):
        df_30.columns = [col[0] for col in df_30.columns]
        
    # Ensure Close is float
    df_5['Close'] = df_5['Close'].astype(float)
    df_30['Close'] = df_30['Close'].astype(float)

    # --- KIS PATCHING ---
    print("⏳ Patching with KIS Real-time Data...")
    df_5 = stitch_kis_candles(ticker, df_5, 5)
    df_30 = stitch_kis_candles(ticker, df_30, 30)
    # --------------------

    # Calculate MAs
    # 5m
    df_5['ma10'] = ta.sma(df_5['Close'], length=10)
    df_5['ma30'] = ta.sma(df_5['Close'], length=30)
    
    # 30m
    df_30['ma10'] = ta.sma(df_30['Close'], length=10)
    df_30['ma30'] = ta.sma(df_30['Close'], length=30)
    
    if df_5['ma10'].iloc[-1] is None or np.isnan(df_5['ma10'].iloc[-1]):
        print("⚠️ Latest 5m MA is NaN. Checking previous values...")
        print(df_5[['Close', 'ma10']].tail())
        # Try finding last valid index or just use -2
        if not np.isnan(df_5['ma10'].iloc[-2]):
             print("⚠️ Using previous candle for verification.")
             # Drop last row if it's incomplete/NaN (often happens with live data fetch)
             df_5 = df_5.iloc[:-1]
             df_30 = df_30.iloc[:-1] # Sync roughly
        else:
             print("❌ 5m MA calculation failed (Persistent NaN)")
             return


    # Get latest
    curr_price = df_5['Close'].iloc[-1]
    
    # Step 1: 5m GC
    ma10_5 = float(df_5['ma10'].iloc[-1])
    ma30_5 = float(df_5['ma30'].iloc[-1])
    step1_on = ma10_5 > ma30_5
    
    # Step 2: LRS
    lrs_val = simple_lrs(df_5['Close'], 10)
    step2_on = (lrs_val > 0)
    
    # Step 3: 30m GC
    # Note: 30m MA calculation might fail if stitched data is not enough or misaligned, but usually fine.
    # Check 30m MA validity
    if np.isnan(df_30['ma10'].iloc[-1]):
         ma10_30 = float(df_30['ma10'].iloc[-2]) if len(df_30) > 1 else 0
         ma30_30 = float(df_30['ma30'].iloc[-2]) if len(df_30) > 1 else 0
    else:
         ma10_30 = float(df_30['ma10'].iloc[-1])
         ma30_30 = float(df_30['ma30'].iloc[-1])
         
    step3_on = ma10_30 > ma30_30
    
    print(f"\n📊 [Verification Results for SOXL] (Time: {datetime.now().strftime('%H:%M:%S')})")
    print(f"   Current Price: ${curr_price:.2f}")
    print("-" * 40)
    
    print(f"✅ Step 1 (5m GC) Status: {'ON' if step1_on else 'OFF'}")
    print(f"   - 5m MA10: {ma10_5:.4f}")
    print(f"   - 5m MA30: {ma30_5:.4f}")
    print(f"   - Result: MA10 ({ma10_5:.2f}) {'>' if step1_on else '<'} MA30 ({ma30_5:.2f})")
    
    print("-" * 40)
    print(f"✅ Step 2 (LRS) Status: {'ON' if step2_on else 'OFF'}")
    print(f"   - 5m LRS(10): {lrs_val:.6f}")
    print(f"   - Result: LRS {'>' if step2_on else '<='} 0")
    
    print("-" * 40)
    print(f"✅ Step 3 (30m GC) Status: {'ON' if step3_on else 'OFF'}")
    print(f"   - 30m MA10: {ma10_30:.4f}")
    print(f"   - 30m MA30: {ma30_30:.4f}")
    print(f"   - Result: MA10 ({ma10_30:.2f}) {'>' if step3_on else '<'} MA30 ({ma30_30:.2f})")
    
    print("-" * 40)
    
    # Final Summary
    print(f"\nFinal Check:")
    if step1_on and step3_on:
        print("⭕ Correct! Step 1 and Step 3 are BOTH ON.")
    else:
        print("❌ Mismatch with user observation.")

if __name__ == "__main__":
    verify_soxl()
