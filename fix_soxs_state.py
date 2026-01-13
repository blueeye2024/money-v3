
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from db import get_connection

def fix_soxs_state():
    ticker = "SOXS"
    print(f"Fixing state for {ticker}...")
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Restore Buy Final to 'Y' (Holding)
            cursor.execute("UPDATE buy_stock SET final_buy_yn='Y' WHERE ticker=%s", (ticker,))
            print("   Updated buy_stock: final_buy_yn = 'Y'")
            
            # 2. Reset Sell Final to 'N' (Not Finished yet)
            # This ensures 'isSellFinished' is false.
            cursor.execute("UPDATE sell_stock SET final_sell_yn='N' WHERE ticker=%s", (ticker,))
            print("   Updated sell_stock: final_sell_yn = 'N'")
            
            # 3. Ensure Sell 2 is 'N' (As user requested cancel)
            # Or should I leave it as they left it? They said they cancelled it.
            # I will ensure it is 'N' just to match their intent.
            cursor.execute("UPDATE sell_stock SET sell_sig2_yn='N' WHERE ticker=%s", (ticker,))
            
        conn.commit()
        print("✅ SOXS State Restored to 'Holding/Sell Monitoring'.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_soxs_state()
