

import requests
import json
import sys

BASE_URL = "http://localhost:9200/api/lab"

def test_partial_calc():
    print("Testing Partial Calculation with REAL IDs...")
    
    # 1. Fetch Data to get IDs
    try:
        res = requests.get(f"{BASE_URL}/data/30m?limit=5&ticker=SOXL")
        if res.status_code != 200:
            print("Failed to fetch data")
            return
            
        data = res.json().get('data', [])
        if not data:
            print("No data found")
            return
            
        ids = [str(d['id']) for d in data]
        ids_str = ",".join(ids)
        print(f"Target IDs: {ids_str}")
        
        # 2. Calculate
        url = f"{BASE_URL}/calculate?period=30m&ticker=SOXL&ids={ids_str}"
        print(f"POST {url}")
        
        res = requests.post(url)
        print(f"Status Code: {res.status_code}")
        
        if res.status_code != 200:
            print("Response Text (First 500 chars):")
            print(res.text[:500])
        else:
            print("Success:", res.json())
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_partial_calc()

