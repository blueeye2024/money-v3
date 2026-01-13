
import os
import sys
# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from db import get_connection, manual_update_signal, get_v2_buy_status, get_v2_sell_status

def test_independence():
    ticker = "TEST_INDEP"
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Clean up
            cursor.execute("DELETE FROM buy_stock WHERE ticker=%s", (ticker,))
            cursor.execute("DELETE FROM sell_stock WHERE ticker=%s", (ticker,))
            
            # 1. Create Buy Record (All Y)
            cursor.execute("""
                INSERT INTO buy_stock (ticker, buy_sig1_yn, buy_sig2_yn, buy_sig3_yn, final_buy_yn, row_dt)
                VALUES (%s, 'Y', 'Y', 'Y', 'Y', NOW())
            """, (ticker,))
            
            # 2. Create Sell Record (Sig1, Sig2 Y)
            cursor.execute("""
                INSERT INTO sell_stock (ticker, sell_sig1_yn, sell_sig2_yn, row_dt)
                VALUES (%s, 'Y', 'Y', NOW())
            """, (ticker,))
        conn.commit()
        
        print("--- Initial State ---")
        buy = get_v2_buy_status(ticker)
        sell = get_v2_sell_status(ticker)
        print(f"Buy 2: {buy['buy_sig2_yn']}")
        print(f"Sell 2: {sell['sell_sig2_yn']}")
        
        if buy['buy_sig2_yn'] != 'Y' or sell['sell_sig2_yn'] != 'Y':
            print("❌ Setup failed")
            return

        # 3. Cancel Sell 2 Manual
        print("\n>>> Cancelling Sell Signal 2 (Manual)...")
        manual_update_signal(ticker, 'sell2', 0, 'N')
        
        # 4. Check Result
        buy_after = get_v2_buy_status(ticker)
        sell_after = get_v2_sell_status(ticker)
        
        print(f"Buy 2 After: {buy_after['buy_sig2_yn']}")
        print(f"Sell 2 After: {sell_after['sell_sig2_yn']}")
        
        if sell_after['sell_sig2_yn'] == 'N' and buy_after['buy_sig2_yn'] == 'Y':
            print("\n✅ SUCCESS: Independence Verified. Buy Signal remained 'Y'.")
        elif buy_after['buy_sig2_yn'] == 'N':
            print("\n❌ FAILURE: Buy Signal also cancelled!")
        else:
            print(f"\n❓ Unknown state: Buy={buy_after['buy_sig2_yn']}, Sell={sell_after['sell_sig2_yn']}")

    finally:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM buy_stock WHERE ticker=%s", (ticker,))
            cursor.execute("DELETE FROM sell_stock WHERE ticker=%s", (ticker,))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    test_independence()
