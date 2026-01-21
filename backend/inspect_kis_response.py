from kis_api_v2 import kis_client
import json

def check_kis():
    ticker = "SOXL"
    interval = 30
    
    print(f"--- Fetching {ticker} (AMS) ---")
    c_ams = kis_client.get_minute_candles(ticker, interval, exchange="AMS")
    if c_ams:
        print(f"AMS Count: {len(c_ams)}")
        print(f"AMS First: {c_ams[0]['kymd']} {c_ams[0]['khms']} (KST)")
        print(f"AMS Last:  {c_ams[-1]['kymd']} {c_ams[-1]['khms']} (KST)")
    else:
        print("AMS: No data")

    print(f"\n--- Fetching {ticker} (BAA) ---")
    c_baa = kis_client.get_minute_candles(ticker, interval, exchange="BAA")
    if c_baa:
        print(f"BAA Count: {len(c_baa)}")
        print(f"BAA First: {c_baa[0]['kymd']} {c_baa[0]['khms']} (KST)")
        print(f"BAA Last:  {c_baa[-1]['kymd']} {c_baa[-1]['khms']} (KST)")
    else:
        print("BAA: No data")

if __name__ == "__main__":
    check_kis()
