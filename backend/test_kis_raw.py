
import sys
import json
import time
from datetime import datetime

# Add backend directory
sys.path.append('/home/blue/blue/my_project/money/backend')
from kis_api_v2 import kis_client

def check_kis_time():
    print(f"Current System Time: {datetime.now()}")
    
    # 1. Force Token Check
    if not kis_client.access_token:
        kis_client._issue_token()
        
    print(f"Token: {kis_client.access_token[:10]}...")
    
    # 2. Raw Request
    # Use internal method to get raw response
    res = kis_client._fetch_price_request("NYS", "SOXL")
    
    if res:
        print("\n=== KIS API Raw Response ===")
        # Pretty print
        print(json.dumps(res, indent=2, ensure_ascii=False))
        
        output = res.get('output', {})
        # Check for time fields (t_time, t_hour etc)
        # Note: HHDFS00000300 response fields might differ
        
    else:
        print("No response from KIS API")

if __name__ == "__main__":
    check_kis_time()
