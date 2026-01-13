
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from db import get_connection, manual_update_signal, get_v2_buy_status, get_v2_sell_status

def test_soxs_bug():
    ticker = "SOXS_TEST"
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Clean up/Reset for Test
            cursor.execute("DELETE FROM buy_stock WHERE ticker=%s", (ticker,))
            cursor.execute("DELETE FROM sell_stock WHERE ticker=%s", (ticker,))
            
            # 1. Setup: Buy Completed (Holding), Sell 1&2 Active
            print("1. Setting up SOXS state: Buy Final=Y, Sell 1=Y, Sell 2=Y")
            cursor.execute("""
                INSERT INTO buy_stock (ticker, buy_sig1_yn, buy_sig2_yn, buy_sig3_yn, final_buy_yn, row_dt)
                VALUES (%s, 'Y', 'Y', 'Y', 'Y', NOW())
            """, (ticker,))
            
            cursor.execute("""
                INSERT INTO sell_stock (ticker, sell_sig1_yn, sell_sig2_yn, row_dt)
                VALUES (%s, 'Y', 'Y', NOW())
            """, (ticker,))
        conn.commit()
        
        # Verify Initial
        buy = get_v2_buy_status(ticker)
        sell = get_v2_sell_status(ticker)
        print(f"   Initial Buy Final: {buy['final_buy_yn']}")
        print(f"   Initial Sell 2: {sell['sell_sig2_yn']}")
        
        if buy['final_buy_yn'] != 'Y':
            print("❌ Setup failed: Buy Final is not Y")
            return

        # 2. Reproduce: Cancel Sell 2
        print("\n2. Action: Cancel Sell 2 (Manual)")
        manual_update_signal(ticker, 'sell2', 0, 'N')
        
        # 3. Check Result
        buy_after = get_v2_buy_status(ticker)
        sell_after = get_v2_sell_status(ticker)
        
        print("\n3. Results:")
        print(f"   Sell 2: {sell_after['sell_sig2_yn']} (Expected: N)")
        
        buy_final_status = buy_after['final_buy_yn'] if buy_after else "None"
        print(f"   Buy Final: {buy_final_status} (Expected: Y)")
        
        buy2_status = buy_after['buy_sig2_yn'] if buy_after else "None"
        print(f"   Buy 2: {buy2_status} (Expected: Y)")

        if buy_final_status == 'Y' and buy2_status == 'Y':
            print("\n✅ PASSED: Buy record remained intact.")
        else:
            print("\n❌ FAILED: Buy record corrupted or deleted!")

    finally:
        pass 
        # Don't delete, let me inspect if needed. 
        # Actually better to restore state or leave it for inspecting via UI? 
        # verification script should be self-contained.
        # But user is using live system. I should probably NOT wipe SOXS data if user is trading.
        # Logic above WIPES SOXS data.
        # I should use a DIFFERENT TICKER for safety, e.g. "SOXS_TEST".
        
if __name__ == "__main__":
    test_soxs_bug()
