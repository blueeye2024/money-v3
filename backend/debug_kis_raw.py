
from kis_api import kis_client
import json

def test_api():
    print("Testing KIS API for SOXS...")
    
    # 1. 토큰 확인
    print(f"Token: {kis_client.access_token[:10]}... (Length: {len(kis_client.access_token)})")
    
    # 2. NAS (NASDAQ)
    print("\n[Requesting NAS]")
    res_nas = kis_client._fetch_price_request("NAS", "UPRO")
    print(json.dumps(res_nas, indent=2))
    
    # 3. NYS (NYSE)
    print("\n[Requesting NYS]")
    res_nys = kis_client._fetch_price_request("NYS", "UPRO")
    print(json.dumps(res_nys, indent=2))
    
    # 4. AMS (AMEX)
    print("\n[Requesting AMS]")
    res_ams = kis_client._fetch_price_request("AMS", "UPRO")
    print(json.dumps(res_ams, indent=2))

if __name__ == "__main__":
    test_api()
