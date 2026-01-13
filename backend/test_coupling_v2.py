
import requests
import json
import sys

BASE_URL = "http://localhost:9100/api/v2"
TICKER = "SOXS"

def get_status():
    try:
        res = requests.get(f"{BASE_URL}/status/{TICKER}")
        if res.status_code == 200:
            return res.json()
        print(f"Error fetching status: {res.status_code}")
        return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

def test_coupling():
    print(f"--- Testing Coupling for {TICKER} (Advanced) ---")
    
    # 0. Setup: Ensure Buy Signal is ON and Holding is ON
    print("\n[Setup] Setting Buy1=Y, FinalBuy=Y (Holding)")
    requests.post(f"{BASE_URL}/manual-signal", json={
        "ticker": TICKER, "signal_key": "buy1", "price": 10, "status": "Y"
    })
    # We need to set final_buy to Y to be in "Holding" mode, otherwise Sell logic might act differently
    # Using confirm-buy API or direct DB? Confirm-buy sets final_buy=Y.
    requests.post(f"{BASE_URL}/confirm-buy", json={
        "ticker": TICKER, "price": 10, "qty": 100, "is_end": False
    })
    
    state1 = get_status()
    buy1 = state1.get('buy', {})
    print(f"Setup State -> Buy1: {buy1.get('buy_sig1_yn')}, FinalBuy: {buy1.get('final_buy_yn')}")
    
    # 1. Set Sell Manual ON
    print("\n[Action] Setting Sell Signal 1 -> Y")
    requests.post(f"{BASE_URL}/manual-signal", json={
        "ticker": TICKER, "signal_key": "sell1", "price": 100, "status": "Y"
    })
    
    state2 = get_status()
    print(f"State After Sell ON -> Buy1: {state2.get('buy', {}).get('buy_sig1_yn')}, Sell1: {state2.get('sell', {}).get('sell_sig1_yn')}")
    
    # 2. Cancel Sell Signal (N)
    print("\n[Action] Canceling Sell Signal 1 -> N")
    requests.post(f"{BASE_URL}/manual-signal", json={
        "ticker": TICKER, "signal_key": "sell1", "price": 100, "status": "N"
    })
    
    state3 = get_status()
    buy3 = state3.get('buy', {})
    sell3 = state3.get('sell', {})
    print(f"State After Sell OFF -> Buy1: {buy3.get('buy_sig1_yn')}, Sell1: {sell3.get('sell_sig1_yn')}")

    if buy3.get('buy_sig1_yn') != 'Y':
         print("❌ CRITICAL: Buy Signal Turned OFF!")
    else:
         print("✅ SUCCESS: Buy Signal remained ON.")

if __name__ == "__main__":
    test_coupling()
