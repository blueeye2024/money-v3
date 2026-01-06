
from kis_api import kis_client
import json

def test_api():
    print("Testing KIS API for SOXS...")
    
    # 1. 토큰 확인
    print(f"Token: {kis_client.access_token[:10]}... (Length: {len(kis_client.access_token)})")
    
    tickers = ["SOXL", "SOXS", "UPRO"]
    for t in tickers:
        print(f"\n[Requesting AMS for {t}]")
        res = kis_client._fetch_price_request("AMS", t)
        print(json.dumps(res, indent=2))

if __name__ == "__main__":
    test_api()
