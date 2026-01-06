
from kis_api import kis_client
import json

print("--- Fetching KIS Raw Minute Data (30m) for SOXL ---")
data = kis_client.get_minute_candles("SOXL", 30)
if data:
    print(f"Count: {len(data)}")
    print("First item:", data[0])
    print("Last item:", data[-1])
else:
    print("No data returned for 30m")

print("\n--- Fetching KIS Raw Minute Data (5m) for SOXL ---")
data = kis_client.get_minute_candles("SOXL", 5)
if data:
    print(f"Count: {len(data)}")
    print("Last 3 items:")
    for d in data[-3:]:
        print(d)
else:
    print("No data returned for 5m")
