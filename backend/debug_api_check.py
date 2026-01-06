
import requests
import json

try:
    print("Fetching http://localhost:8000/api/report ...")
    r = requests.get("http://localhost:8000/api/report", timeout=30)
    print(f"Status: {r.status_code}")
    
    data = r.json()
    
    # Check Market Regime SOXL
    soxl = data.get('market_regime', {}).get('details', {}).get('soxl', {})
    history = soxl.get('cross_history', {})
    
    print("\n--- SOXL History Check ---")
    if not history:
        print("FAIL: No cross_history found")
    else:
        g30 = history.get('gold_30m', [])
        print(f"Gold 30m Count: {len(g30)}")
        if g30:
            print("First Item:", g30[0])
            if 'time_kr' in g30[0] and 'time_ny' in g30[0]:
                print("SUCCESS: Time fields present")
            else:
                print("FAIL: Time fields missing")
        else:
             print("WARNING: Empty 30m history list")
             
except Exception as e:
    print(f"Error: {e}")
