
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from db import create_trade, check_open_trade
from datetime import datetime
import pytz

def force_trade():
    ticker = "SOXL"
    price = 50.55
    ny_tz = pytz.timezone('America/New_York')
    entry_time = datetime.now(ny_tz)
    
    print(f"Checking open trade for {ticker}...")
    if check_open_trade(ticker):
        print(f"Trade already open for {ticker}.")
        return

    print(f"Creating Forced Trade for {ticker} at {price}...")
    create_trade(ticker, price, entry_time)
    print("✅ Trade Created!")

if __name__ == "__main__":
    force_trade()
