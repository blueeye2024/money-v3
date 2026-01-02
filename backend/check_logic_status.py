
import sys
import pandas as pd
from datetime import datetime
import pytz

# Add backend directory
sys.path.append('/home/blue/blue/my_project/money/backend')
from analysis import check_triple_filter
from db import load_market_candles

def diagnose():
    print("=== Market Regime Diagnosis ===")
    
    for ticker in ["SOXL", "SOXS"]:
        print(f"\nScanning {ticker}...")
        
        # Load Data directly from DB
        df30 = load_market_candles(ticker, "30m", limit=300)
        df5 = load_market_candles(ticker, "5m", limit=300)
        
        if df30 is None or df30.empty:
            print("  ❌ No 30m Data found in DB")
            continue
            
        print(f"  📊 30m Data Loaded: {len(df30)} candles")
        print(f"     Last Candle Time: {df30.index[-1]}")
        
        if df5 is not None and not df5.empty:
            print(f"  📊 5m Data Loaded: {len(df5)} candles")
            print(f"     Last 5m Time: {df5.index[-1]}")
        else:
            print("  ❌ No 5m Data found in DB (This causes WAIT signal)")
        
        # Check Logic
        res = check_triple_filter(ticker, df30, df5)
        
        print("  🔍 Logic Result:")
        print(f"     - Current Price: {res.get('current_price')}")
        print(f"     - Daily Change: {res.get('daily_change')}%")
        print(f"     - Final Signal: {'✅ ACTION' if res.get('final') else '🚫 WAIT'}")
        print(f"     - Step 1 (5m Timing): {res.get('step1')} ({res['step_details']['step1']})")
        print(f"     - Step 2 (30m Trend): {res.get('step2')} ({res['step_details']['step2']})")
        print(f"     - Step 3 (2% Strength): {res.get('step3')} ({res['step_details']['step3']})")

if __name__ == "__main__":
    diagnose()
