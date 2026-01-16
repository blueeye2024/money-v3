
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from kis_api_v2 import kis_client
import datetime
import pytz

def test_overnight():
    print("Fetching KIS SOXL 30m Data to check overnight coverage...")
    
    # 30m candles
    data = kis_client.get_minute_candles("SOXL", 30, exchange="NYS")
    
    if not data:
        print("Failed to fetch data or no data returned.")
        return

    print(f"Received {len(data)} candles.")
    
    # Parse and print
    found_overnight = False
    ny_tz = pytz.timezone('America/New_York')
    kst_tz = pytz.timezone('Asia/Seoul')
    
    for item in data:
        # KIS Time: YYYYMMDD HHMMSS (KST)
        dt_str = f"{item['kymd']} {item['khms']}"
        dt_kst = datetime.datetime.strptime(dt_str, "%Y%m%d %H%M%S")
        dt_kst = kst_tz.localize(dt_kst)
        dt_ny = dt_kst.astimezone(ny_tz)
        
        # Check if time is between 00:00 and 04:00 NY
        h = dt_ny.hour
        is_overnight = (0 <= h < 4)
        
        prefix = "🌙 OVERNIGHT" if is_overnight else "☀️ REGULAR/PRE"
        
        print(f"[{prefix}] KST: {dt_kst} | NY: {dt_ny} | Price: {item['last']}")
        
        if is_overnight:
            found_overnight = True

    if found_overnight:
        print("\n✅ KIS API returns Overnight Data (00:00-04:00 NY)!")
    else:
        print("\n❌ KIS API does NOT return Overnight Data. Only Pre/Regular/Post found.")

if __name__ == "__main__":
    test_overnight()
