
from kis_api_v2 import get_minute_candles
import pandas as pd
from datetime import datetime

print("TESTing KIS Minute Chart...")

# fetch 30m
data_30 = get_minute_candles("SOXL", 30)
if data_30:
    print(f"\n[SOXL 30m] Fetched {len(data_30)} items")
    # item format: {'kymd': '20250106', 'khms': '103000', 'open': '50.1400', 'high': '50.6900', 'low': '49.8200', 'last': '50.3800', 'vol': '123456'}
    # Time is local (Exchange time? or KST?) Usually KIS provides KST in kymd/khms
    # Let's check the latest one
    latest = data_30[0] # List is usually reversed (recent first)? or standard? 
    print(f"Latest 30m: {latest['kymd']} {latest['khms']} Price: {latest['last']}")
    print(f"Keys: {list(latest.keys())}")
    
else:
    print("Failed to fetch 30m")

# fetch 5m
data_5 = get_minute_candles("SOXL", 5)
if data_5:
    print(f"\n[SOXL 5m] Fetched {len(data_5)} items")
    latest = data_5[0]
    print(f"Latest 5m: {latest['kymd']} {latest['khms']} Price: {latest['last']}")
else:
    print("Failed to fetch 5m")
