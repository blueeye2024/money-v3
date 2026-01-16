import sys
import os
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from kis_api_v2 import kis_client

def check_soxl():
    print("\n--- KIS API SOXL Realtime Check ---")
    ticker = "SOXL"
    exchange = "NYS"
    
    print(f"Ticker: {ticker}")
    
    # Try AMS (Default in code)
    print("Trying AMS (Default)...")
    data_ams = kis_client.get_price(ticker, "AMS")
    print(f"AMS Data: {json.dumps(data_ams, indent=2)}")

    # Try NYS
    print("Trying NYS...")
    data_nys = kis_client.get_price(ticker, "NYS")
    print(f"NYS Data: {json.dumps(data_nys, indent=2)}")



if __name__ == "__main__":
    check_soxl()
