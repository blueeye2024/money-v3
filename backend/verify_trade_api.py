
import requests
import json
import logging

URL = "http://localhost:9100/api/report"

def check_trade_history():
    try:
        print(f"Fetching {URL} ...")
        res = requests.get(URL, timeout=10)
        if res.status_code != 200:
            print(f"Error: Status {res.status_code}")
            return
            
        data = res.json()
        
        # Navigate to trade_history
        # Structure: market_regime -> details -> prime_guide -> trade_history
        
        try:
            regime = data.get('market_regime', {})
            details = regime.get('details', {})
            prime = details.get('prime_guide', {})
            trades = prime.get('trade_history', [])
            
            print(f"\n--- Trade History (Count: {len(trades)}) ---")
            for t in trades:
                print(f"Ticker: {t['ticker']} | Status: {t['status']} | Entry: {t['entry_time']} @ ${t['entry_price']}")
                
            if len(trades) > 0:
                print("\n✅ Verification SUCCESS: Trade history is populated.")
            else:
                print("\n⚠️ Verification WARNING: Trade history is empty.")
                
        except Exception as e:
            print(f"JSON Parsing Error: {e}")
            print(json.dumps(data, indent=2)[:500])
            
    except Exception as e:
        print(f"Request Failed: {e}")

if __name__ == "__main__":
    check_trade_history()
