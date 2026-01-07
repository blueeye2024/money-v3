
import sys
import os

# Add backend to path
sys.path.append('/home/blue/blue/my_project/money/backend')
from db import create_v2_sell_record

def manual_create_sell():
    manage_id = "SOXS20260107_1820"
    ticker = "SOXS"
    entry_price = 2.44
    
    print(f"Manually creating Sell Record for {manage_id}...")
    if create_v2_sell_record(manage_id, ticker, entry_price):
        print("✅ Success!")
    else:
        print("❌ Failed (Maybe already exists?)")

if __name__ == "__main__":
    manual_create_sell()
