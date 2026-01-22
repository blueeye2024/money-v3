import sys
import os
import pandas as pd
from datetime import datetime

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.append(os.path.dirname(__file__))

from backend.analysis import analyze_ticker, fetch_data, get_detailed_market_regime
from backend.db import get_stock_current_price

def verify_intelligence():
    tickers = ['SOXL', 'SOXS']
    print(f"🔍 Verifying Market Intelligence Center for {tickers}...")
    
    # 1. Fetch Latest Prices (DB/API Real-time View)
    print("\n[1. Real-time Price Check (DB/API)]")
    current_prices = {}
    for t in tickers:
        p = get_stock_current_price(t)
        if p:
            print(f"  ✅ {t}: ${p['price']} (Change: {p.get('change_pct', 0)}%)")
            current_prices[t] = p['price']
        else:
            print(f"  ❌ {t}: Failed to fetch price")

    # 2. Run Analysis Logic (Backend Calculation View)
    # This simulates what run_analysis() does
    print("\n[2. Analysis Engine Data Check]")
    print("  Fetching data (force=True)...")
    try:
        data_30m, data_5m, _, _, _ = fetch_data(tickers, force=True)
    except Exception as e:
        print(f"  ❌ Fetch Error: {e}")
        return

    # Check Regime/Prime Guide
    regime = get_detailed_market_regime(data_30m, data_5m)
    
    for t in tickers:
        df5 = data_5m.get(t)
        df30 = data_30m.get(t)
        
        if df5 is not None and not df5.empty:
            last_close = df5['Close'].iloc[-1]
            last_time = df5.index[-1]
            
            curr_price = current_prices.get(t, 0)
            diff = abs(curr_price - last_close)
            
            print(f"\n📊 {t} Analysis Context:")
            print(f"  - Real-time Price: ${curr_price}")
            print(f"  - Analysis Last Close: ${last_close} (at {last_time})")
            
            if diff > (curr_price * 0.005): # 0.5% diff warning
                print(f"  ⚠️ WARNING: Significant price divergence (${diff:.2f})")
            else:
                print(f"  ✅ Data Synchronization: Good")

            # Analyze Ticker to get Metrics
            result = analyze_ticker(t, df5, df30)
            metrics = result.get('new_metrics', {})
            
            print(f"  [Metrics]")
            print(f"  - RSI (14): {metrics.get('rsi'):.2f}")
            print(f"  - Vol Ratio: {metrics.get('vol_ratio'):.2f}")
            print(f"  - ATR: {metrics.get('atr'):.2f}")
            print(f"  - Pivot R1: {metrics.get('pivot', {}).get('r1'):.2f}")
            print(f"  - MACD: {result.get('macd'):.4f} / Sig: {result.get('macd_sig'):.4f}")
            
            # Check Prime Guide Score
            guide = regime.get('prime_guide', {}).get('scores', {}).get(t, {})
            score = guide.get('score', 0)
            cheongan = guide.get('breakdown', {}).get('cheongan', 0)
            tech = guide.get('breakdown', {}).get('tech', 0)
            
            print(f"  [Prime Guide Score]")
            print(f"  - Total: {score} (Cheongan: {cheongan} + Tech: {tech})")
            
            # Consistency Check
            if score == 0 and metrics.get('rsi') > 0:
                print("  ⚠️ WARNING: Score is 0 but metrics exist. Verify scoring logic.")
        else:
            print(f"  ❌ {t}: No DataFrame data found")

if __name__ == "__main__":
    verify_intelligence()
