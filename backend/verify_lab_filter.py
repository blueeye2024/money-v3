
import requests
import json
import sys

BASE_URL = "http://localhost:9100/api/lab"

def test_filters():
    print("Testing Lab Filters...")
    
    # 1. Test Status Filter (COMPLETE)
    try:
        res = requests.get(f"{BASE_URL}/data/30m?status=COMPLETE&limit=1")
        if res.status_code == 200:
            data = res.json().get('data', [])
            print(f"COMPLETE Filter: OK (Rows: {len(data)})")
        else:
            print(f"COMPLETE Filter: FAILED {res.status_code} {res.text}")
    except Exception as e:
        print(f"COMPLETE Filter: ERROR {e}")

    # 2. Test Status Filter (INCOMPLETE)
    try:
        res = requests.get(f"{BASE_URL}/data/30m?status=INCOMPLETE&limit=1")
        if res.status_code == 200:
            data = res.json().get('data', [])
            print(f"INCOMPLETE Filter: OK (Rows: {len(data)})")
        else:
            print(f"INCOMPLETE Filter: FAILED {res.status_code} {res.text}")
    except Exception as e:
        print(f"INCOMPLETE Filter: ERROR {e}")

    # 3. Test ID Calculation (Mock ID 1)
    # We verify it accepts the param, even if ID 1 doesn't exist or is already calc.
    try:
        res = requests.post(f"{BASE_URL}/calculate?period=30m&ticker=SOXL&ids=1")
        if res.status_code == 200:
            print(f"ID Calculation: OK ({res.json()})")
        else:
            print(f"ID Calculation: FAILED {res.status_code} {res.text}")
    except Exception as e:
        print(f"ID Calculation: ERROR {e}")

if __name__ == "__main__":
    test_filters()
