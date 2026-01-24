import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from db import get_connection, manual_update_signal, get_v2_buy_status

def verify():
    ticker = "TM1"
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Clean up
            cursor.execute("DELETE FROM buy_stock WHERE ticker=%s", (ticker,))
        conn.commit()

        print("--- Step 1: Initial State (No Record) ---")
        
        # Call Manual Update (Simulate User Click)
        print(f"Calling manual_update_signal({ticker}, 'buy1', 100, 'Y')")
        manual_update_signal(ticker, 'buy1', 100, 'Y')

        # Check DB
        status = get_v2_buy_status(ticker)
        print(f"DB State after Insert: {status}")
        
        if status['buy_sig1_yn'] == 'Y':
            print("❌ FAIL: buy_sig1_yn is 'Y'. It should be 'N'.")
        else:
            print("✅ PASS: buy_sig1_yn is 'N'.")

        if status['is_manual_buy1'] != 'Y':
             print("❌ FAIL: is_manual_buy1 is NOT 'Y'.")
        else:
             print("✅ PASS: is_manual_buy1 is 'Y'.")

        # Step 2: Update existing (Simulate Buy 2)
        # First ensure buy1 exists (it does)
        
        print("\n--- Step 2: Update Existing (Buy 2) ---")
        print(f"Calling manual_update_signal({ticker}, 'buy2', 105, 'Y')")
        manual_update_signal(ticker, 'buy2', 105, 'Y')
        
        status = get_v2_buy_status(ticker)
        print(f"DB State after Update: {status}")

        if status['buy_sig2_yn'] == 'Y':
            print("❌ FAIL: buy_sig2_yn is 'Y'. It should be 'N'.")
        else:
            print("✅ PASS: buy_sig2_yn is 'N'.")
            
        if status['is_manual_buy2'] != 'Y':
             print("❌ FAIL: is_manual_buy2 is NOT 'Y'.")
        else:
             print("✅ PASS: is_manual_buy2 is 'Y'.")

    finally:
        conn.close()

if __name__ == "__main__":
    verify()
