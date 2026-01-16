
import sys
import requests
import json
import time

# Add backend directory to load KIS Client
sys.path.append('/home/blue/blue/my_project/money/backend')
from kis_api_v2 import kis_client

def test_detail():
    print("Testing KIS Detail API for SOXL...")
    
    token = kis_client.access_token
    if not token:
        token = kis_client._issue_token()
    
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": kis_client.APP_KEY,
        "appsecret": kis_client.APP_SECRET,
        "tr_id": "HHDFS76200200" # Detail API
    }
    
    params = {
        "AUTH": "",
        "EXCD": "NYS",
        "SYMB": "SOXL"
    }
    
    try:
        url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/price-detail"
        print(f"Requesting to {url}...")
        res = requests.get(url, headers=headers, params=params, timeout=5)
        print(f"Status: {res.status_code}")
        
        if res.status_code == 200:
            data = res.json()
            print("Response:", json.dumps(data, indent=2))
            
            out = data.get('output')
            if out:
                print(f"Last Price: {out.get('last')}")
                print(f"Base Price: {out.get('base')}")
        else:
            print("Error:", res.text)
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_detail()
