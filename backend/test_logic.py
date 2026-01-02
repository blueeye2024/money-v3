
import sys
import os
import pandas as pd
from datetime import datetime

# Add backend directory to sys.path
sys.path.append('/home/blue/blue/my_project/money/backend')

from analysis import check_triple_filter

def test_soxl():
    print("Testing check_triple_filter for SOXL...")
    
    # Mock Data
    df30 = pd.DataFrame({'Close': [40.0]*50 + [42.0]*10, 'High': [43.0]*60})
    df5 = pd.DataFrame({'Close': [41.0]*50 + [42.0]*10})
    
    # Run
    try:
        result = check_triple_filter("SOXL", df30, df5)
        print("\n=== Result ===")
        print(f"current_price: {result.get('current_price')}")
        print(f"daily_change: {result.get('daily_change')}")
        print(f"entry_price: {result.get('entry_price')}")
        print(f"Result Keys: {list(result.keys())}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_soxl()
