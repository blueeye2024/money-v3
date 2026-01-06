
from kis_api import kis_client
import json

def test_api():
    print("Testing KIS API for SOXS...")
    
    # 1. 토큰 확인
    print(f"Token: {kis_client.access_token[:10]}... (Length: {len(kis_client.access_token)})")
    
    print("\n[Testing Daily Price for SOXL]")
    daily = kis_client.get_daily_price("SOXL", "AMS")
    if daily:
        print(json.dumps(daily[:2], indent=2))
    else:
        print("Failed to get daily price")

if __name__ == "__main__":
    test_api()
