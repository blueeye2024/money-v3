
from kis_api import kis_client
import json

def test_api():
    print("Testing KIS API for SOXS...")
    
    # 1. 토큰 확인
    print(f"Token: {kis_client.access_token[:10]}... (Length: {len(kis_client.access_token)})")
    
    tickers = ["SOXL", "SOXS", "UPRO"]
    for t in tickers:
        print(f"\n[{t}]")
        # 1. Current Price
        # Exchange is AMS for all these based on previous fixes
        kp = kis_client.get_price(t, "AMS")
        if kp:
            print(f"  Current: {kp['price']} (Rate: {kp['rate']}%)")
        else:
            print("  Current: Failed")
            
        # 2. Daily Price (Yesterday)
        daily = kis_client.get_daily_price(t, "AMS")
        if daily and len(daily) > 1:
            prev = daily[1]
            print(f"  Yesterday({prev['xymd']}): Close {prev['clos']} (Rate {prev['rate']}%)")
        else:
            print("  Daily: Failed")

if __name__ == "__main__":
    test_api()
