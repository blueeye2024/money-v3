import sys
import os
import pandas as pd
import pandas_ta as ta
import yfinance as yf

# Append backend path
sys.path.append('/home/blue/blue/my_project/money/backend')
from analysis import fetch_data, calculate_sma

def diagnose_soxl():
    print("=== Diagnosing SOXL 5m Signal Logic ===")
    ticker = "SOXS"
    
    # Fetch 5m data
    print(f"Fetching 5m data for {ticker}...")
    # fetch_data returns: data_30m, data_5m, data_1d, market_data, regime_info
    # Pass ticker as a list ["SOXL"]
    _, data_5m, _, _, _ = fetch_data([ticker], force=True)
    
    # data_5m is a dict {ticker: df} or just df if single? 
    # fetch_data behavior: if multiple tickers, it returns a dict-like or multi-index df?
    # yf.download with group_by='ticker' returns MultiIndex columns if >1 ticker.
    # But if 1 ticker?
    # Analysis.py:
    # return _DATA_CACHE["30m"], ...
    # Let's inspect data_5m structure.
    
    if data_5m is None:
        print("Failed to fetch 5m data.")
        return

    # If yfinance returns single ticker, columns are just Open, High...
    # But analysis.py usually handles dictionary structure or single DF.
    # Let's assume it returns a raw DF for the requested tickers if cached.
    # Wait, analysis.py line 205: `df_30mRaw = data_30m[ticker]` implies data_30m is a dict or MultiIndex.
    # But `yf.download` return format varies.
    
    # Safely get DF
    try:
        df_5m = data_5m[ticker]
    except:
        df_5m = data_5m # Fallback if it's already the DF

    if df_5m is None or df_5m.empty:
        print("df_5m is empty.")
        return

    from analysis import calculate_tech_indicators, calculate_sma
    
    # Calculate indicators
    df_5m['SMA_5'] = calculate_sma(df_5m['Close'], 5)
    df_5m['SMA_20'] = calculate_sma(df_5m['Close'], 20)
    calculate_tech_indicators(df_5m) # modifies in-place for RSI
    
    # Get last 5 rows
    recent = df_5m.tail(5)
    print("\nRecent 5m Data (Last 5 candles):")
    print(recent[['Close', 'SMA_5', 'SMA_20', 'RSI']])
    
    curr = df_5m.iloc[-1]
    prev = df_5m.iloc[-2]
    
    print("\n--- Logic Check ---")
    
    # 1. 5m MA Trend (Catch-up Logic defined in Analysis.py as Alignment)
    # Analysis.py: is_5m_trend_up = (ma5_5 > ma20_5)
    ma5_curr = curr['SMA_5']
    ma20_curr = curr['SMA_20']
    
    # Original 'Trend Up' (Slope) check:
    ma20_prev = prev['SMA_20']
    slope_up = ma20_curr > ma20_prev
    
    # Analysis.py Def:
    is_5m_trend_up = (ma5_curr > ma20_curr)
    
    print(f"1. 5m Alignment (Catch-up)? {is_5m_trend_up} (MA5: {ma5_curr:.4f} > MA20: {ma20_curr:.4f})")
    print(f"   (MA20 Slope Up? {slope_up})")
    
    # 2. Golden Cross (MA5 > MA20)
    # Check strict crossover (Prev MA5 <= Prev MA20 AND Curr MA5 > Curr MA20)
    # Or just current state?
    # Analysis.py:
    # is_5m_gc = (prev['SMA_5'] <= prev['SMA_20']) and (curr['SMA_5'] > curr['SMA_20'])
    is_5m_gc = (prev['SMA_5'] <= prev['SMA_20']) and (curr['SMA_5'] > curr['SMA_20'])
    print(f"2. 5m Golden Cross (Strict)? {is_5m_gc}")
    print(f"   Prev: MA5({prev['SMA_5']:.4f}) <= MA20({prev['SMA_20']:.4f})")
    print(f"   Curr: MA5({curr['SMA_5']:.4f}) > MA20({curr['SMA_20']:.4f})")
    
    # Catch-up Logic check (Trend Up + MA5 > MA20)
    # Note: Analysis.py uses `is_5m_gc or is_trend_up` depending on context?
    # Actually Step 1 is usually just GC or Trend.
    # In V2 logic:
    # cond_1 = (is_5m_gc and is_5m_trend_up)
    
    print(f"\nCondition 1 (GC + Trend Up): {is_5m_gc and is_5m_trend_up}")
    
    # Check RSI
    rsi_ok = curr['RSI'] < 70
    print(f"RSI < 70? {rsi_ok} ({curr['RSI']:.2f})")
    
    print("\n=== End Diagnosis ===")

if __name__ == "__main__":
    diagnose_soxl()
