import sys
import os
import pytz
from datetime import datetime, timezone
import yfinance as yf
import pandas as pd

# Mock KIS Client for analysis (or import actual if possible)
try:
    sys.path.append('/home/blue/blue/my_project/money/backend')
    from kis_api import KISClient
    kis_client = KISClient()
except:
    print("KIS Client load failed, will rely on YF fallback logic test")
    kis_client = None

def diagnose_ticker(ticker):
    print(f"\n[{ticker}] Diagnosing Filter 2 (Breakout)...")
    
    # 1. Get Current Price
    current_price = 0
    try:
        # Try KIS Current Price
        if kis_client:
            p = kis_client.get_current_price(ticker)
            if p:
                current_price = float(p.get('price', 0))
                print(f"  > Current Price (KIS): ${current_price}")
            else:
                print("  > Current Price (KIS): None")
        
        if current_price == 0:
            t = yf.Ticker(ticker)
            current_price = t.fast_info.last_price
            print(f"  > Current Price (YF): ${current_price}")
    except Exception as e:
        print(f"  > Error fetching current price: {e}")

    # 2. Logic from analysis.py for Prev Close
    prev_close = None
    
    # Priority 1: KIS
    try:
        if kis_client:
            k_daily = kis_client.get_daily_price(ticker)
            if k_daily and len(k_daily) > 1:
                # KIS daily returns [0]=Today, [1]=Yesterday in many cases
                # Verify structure
                print(f"  > KIS Daily Raw [0]: {k_daily[0]}")
                print(f"  > KIS Daily Raw [1]: {k_daily[1]}")
                prev_close = float(k_daily[1]['clos']) 
                print(f"  > Prev Close (KIS): ${prev_close}")
    except Exception as e:
        print(f"  > KIS Daily Fetch Failed: {e}")

    # Priority 2: YF Fallback
    if not prev_close:
        try:
            print("  > Trying YF Fallback...")
            ticker_obj = yf.Ticker(ticker)
            df_1d = ticker_obj.history(period="5d", interval="1d")
            
            if df_1d is not None and not df_1d.empty:
                 est_tz = pytz.timezone('US/Eastern')
                 today_est = datetime.now(est_tz).date()
                 last_lbl = df_1d.index[-1]
                 last_date = last_lbl.date() if hasattr(last_lbl, 'date') else last_lbl.date()
                 
                 print(f"    - YF Last Date: {last_date} (Today EST: {today_est})")
                 print(f"    - DataFrame Tail:\n{df_1d.tail(3)[['Close']]}")
                 
                 if last_date >= today_est:
                     if len(df_1d) >= 2:
                         prev_close = float(df_1d['Close'].iloc[-2])
                         print(f"    - Using iloc[-2] (Yesterday): ${prev_close}")
                     else:
                         print("    - Not enough data for iloc[-2]")
                 else:
                     prev_close = float(df_1d['Close'].iloc[-1])
                     print(f"    - Using iloc[-1] (Last available): ${prev_close}")
        except Exception as e:
            print(f"  > YF Fallback Failed: {e}")

    # 3. Calculate Target
    target_v = 0
    is_breakout = False
    
    if prev_close and prev_close > 0:
        target_v = round(prev_close * 1.02, 2)
        print(f"  > Logic: Target (+2%) = {prev_close} * 1.02 = ${target_v}")
        
        if current_price >= target_v:
            is_breakout = True
            print("  > RESULT: BREAKOUT [YES] (Current >= Target)")
        else:
            diff = target_v - current_price
            pct = ((current_price - prev_close) / prev_close) * 100
            print(f"  > RESULT: BREAKOUT [NO] (Short by ${diff:.2f}, Current Change: {pct:.2f}%)")
    else:
        print("  > RESULT: FAILED (Prev Close not found)")

if __name__ == "__main__":
    diagnose_ticker("SOXL")
    diagnose_ticker("SOXS")
