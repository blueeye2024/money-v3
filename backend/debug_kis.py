
import sys
import os

# Add backend to path
sys.path.append('/home/blue/blue/my_project/money/backend')

from kis_api import kis_client

def test_price():
    ticker = "SOXL"
    
    print(f"--- Checking {ticker} Prices ---")
    
    # Check AMS (Main)
    print("\n1. Checking AMS (Main Exchange)...")
    res_ams = kis_client.get_price(ticker, 'AMS')
    print(f"AMS Result: {res_ams}")
    
    # Check BAA (Daytime/Extended)
    print("\n2. Checking BAA (Daytime/Extended)...")
    res_baa = kis_client.get_price(ticker, 'BAA')
    print(f"BAA Result: {res_baa}")

    # Check Default Logic
    print("\n3. Checking Default Logic (get_current_price)...")
    from kis_api import get_current_price
    final = get_current_price(ticker)
    print(f"Final Auto Result: {final}")

if __name__ == "__main__":
    test_price()
