import sys
import os
import pandas as pd

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))

try:
    from analysis import check_triple_filter
    from kis_api_v2 import kis_client
    
    ticker = "SOXL"
    print(f"Testing check_triple_filter for {ticker}...")
    
    # Simulate empty/stale dataframes
    df_empty = pd.DataFrame()
    
    # This should trigger the [FIX] logic if KIS is working
    result = check_triple_filter(ticker, df_empty, df_empty)
    
    print("\n--- Result ---")
    print(f"Current Price: {result.get('current_price')}")
    print(f"Step 1: {result.get('step1')}")
    
    # Check if price matches KIS
    kis_p = kis_client.get_price(ticker)
    print(f"\nDirect KIS Price: {kis_p.get('price') if kis_p else 'None'}")
    
    if result.get('current_price') == kis_p.get('price'):
        print("\nSUCCESS: check_triple_filter is using KIS price!")
    else:
        print("\nFAILURE: check_triple_filter is NOT using KIS price.")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
