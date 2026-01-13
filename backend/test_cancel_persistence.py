
import requests
import json
import pymysql
from db import get_connection

BASE_URL = "http://localhost:9100/api/v2"
TICKER = "SOXS"

def check_db_target():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT manual_target_sell1, sell_sig1_yn FROM sell_stock WHERE ticker=%s", (TICKER,))
            row = cursor.fetchone()
            return row
    finally:
        conn.close()

def main():
    print("--- Testing Cancel Persistence ---")
    
    # 1. Setup: Set a Target
    print("\n[Setup] Setting Manual Target Sell1 = 100")
    requests.post(f"{BASE_URL}/manual-signal", json={
        "ticker": TICKER, "signal_key": "sell1", "price": 100, "status": "SET_TARGET"
    })
    
    row = check_db_target()
    print(f"DB State After Set: Target={row['manual_target_sell1']}, Signal={row['sell_sig1_yn']}")
    
    # 2. Simulate User Cancel
    print("\n[Action] Sending Cancel (N)")
    requests.post(f"{BASE_URL}/manual-signal", json={
        "ticker": TICKER, "signal_key": "sell1", "price": 0, "status": "N"
    })
    
    # 3. Verify
    row_after = check_db_target()
    print(f"DB State After Cancel: Target={row_after['manual_target_sell1']}, Signal={row_after['sell_sig1_yn']}")
    
    if row_after['manual_target_sell1'] is None:
        print("✅ SUCCESS: Target cleared to NULL.")
    else:
        print(f"❌ FAILURE: Target persists! ({row_after['manual_target_sell1']})")

if __name__ == "__main__":
    main()
