from analysis import fetch_data
import pandas as pd

print("Fetching Data...")
data_30m, data_5m, data_1d, _, _ = fetch_data(['SOXL'], force=True)

if 'SOXL' in data_1d:
    df = data_1d['SOXL']
    print("\n[SOXL Daily Data Head]")
    print(df.tail(5))
    
    if len(df) >= 2:
        prev_close = float(df['Close'].iloc[-2])
        curr_close = float(df['Close'].iloc[-1])
        print(f"\nCalculated Prev Close (iloc[-2]): {prev_close}")
        print(f"Current Daily Close (iloc[-1]): {curr_close}")
        
        # Check condition
        dummy_curr = 60.11
        is_drop = (prev_close > 0 and dummy_curr <= prev_close)
        print(f"Check with Price 60.11: {dummy_curr} <= {prev_close} ? -> {is_drop}")
    else:
        print("Not enough daily data.")
else:
    print("SOXL not in data_1d")
