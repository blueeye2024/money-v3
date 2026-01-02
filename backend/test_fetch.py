
import sys
import os
import time

# Add backend directory
sys.path.append('/home/blue/blue/my_project/money/backend')

from analysis import fetch_data

def test_fetch_logic():
    print("=== Testing DB-Centric Fetch Logic ===")
    
    start = time.time()
    data_30m, data_5m, _, _, _ = fetch_data() # First run (Init)
    end = time.time()
    
    print(f"\nTime Taken: {end - start:.2f}s")
    
    soxl_30 = data_30m.get("SOXL")
    if soxl_30 is not None:
        print(f"SOXL 30m Count: {len(soxl_30)}")
        print(f"Last Candle: {soxl_30.index[-1]}")
    else:
        print("SOXL 30m: None")
        
    print("\n--- 2nd Run (Incremental) ---")
    start = time.time()
    data_30m, _, _, _, _ = fetch_data() # Second run (Should be fast or use cache)
    end = time.time()
    print(f"Time Taken: {end - start:.2f}s")

if __name__ == "__main__":
    test_fetch_logic()
