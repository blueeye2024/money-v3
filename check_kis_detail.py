
import sys
import os

# Add backend to path
sys.path.append('/home/blue/blue/my_project/money/backend')
from kis_api import kis_client, get_exchange_code

def check_kis_detail():
    ticker = "SOXS"
    exchange = get_exchange_code(ticker)
    
    # We need to check if there is a method to get "Detailed Price" which includes prev close.
    # Looking at kis_api.py (will read it next if this fails, but guessing standard method names)
    # The current code uses 'get_price' which might be simple.
    
    # Let's try raw request via client to specific endpoint if known, 
    # OR better, read kis_api.py to see available methods first.
    # Since I cannot read in this step, I will rely on existing 'get_price' to see what it returns.
    
    print(f"Checking KIS Price for {ticker}...")
    res = kis_client.get_price(ticker, exchange)
    print("Result:", res)
    
    # Also check if we can fetch daily chart to get prev close
    # res_daily = kis_client.get_minute_candles(ticker, "D") # Interval 'D'? logic usually supports numbers
    # But usually API has separate Daily Chart.
    
    # Let's just print the get_price result first.

if __name__ == "__main__":
    check_kis_detail()
