import sys
import os
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import get_connection, confirm_v2_buy, fetch_signal_status_dict

def reset_soxs():
    conn = get_connection()
    with conn.cursor() as cursor:
        # Reset SOXS to initial state (Everything N)
        cursor.execute("DELETE FROM buy_stock WHERE ticker='SOXS'")
        cursor.execute("DELETE FROM sell_stock WHERE ticker='SOXS'")
        
        # Insert initial N state
        cursor.execute("""
            INSERT INTO buy_stock (ticker, buy_sig1_yn, buy_sig2_yn, buy_sig3_yn, final_buy_yn, real_buy_yn, row_dt)
            VALUES ('SOXS', 'N', 'N', 'N', 'N', 'N', NOW())
        """)
    conn.commit()
    conn.close()
    print("✅ SOXS Reset Complete (All N)")

def test_force_entry():
    print("--- Testing Manual Force Entry ---")
    
    # 1. Reset
    reset_soxs()
    
    # 2. Check Initial Status
    status = fetch_signal_status_dict('SOXS')
    buy = status.get('buy')
    print(f"Initial: Sig1={buy['buy_sig1_yn']}, Final={buy['final_buy_yn']}, Real={buy['real_buy_yn']}")
    
    # 3. Simulate "Real Buy Confirmed" (Force Entry)
    print("🚀 Executing confirm_v2_buy (Force Entry)...")
    success, msg = confirm_v2_buy('SOXS', 10.50, 100)
    
    if success:
        print(f"✅ DB Update Success: {msg}")
    else:
        print(f"❌ DB Update Failed: {msg}")
        return

    # 4. Verify Forced Status
    status_new = fetch_signal_status_dict('SOXS')
    buy_new = status_new.get('buy')
    
    print("\n--- Verification ---")
    print(f"Real Buy YN: {buy_new['real_buy_yn']} (Expected: Y)")
    print(f"Final Buy YN: {buy_new['final_buy_yn']} (Expected: Y)")
    print(f"Sig1 YN: {buy_new['buy_sig1_yn']} (Expected: Y)")
    print(f"Manual1: {buy_new['is_manual_buy1']} (Expected: Y)")
    
    if buy_new['final_buy_yn'] == 'Y' and buy_new['is_manual_buy1'] == 'Y':
        print("\n🎉 SUCCESS: Force Entry Logic Verified!")
    else:
        print("\n❌ ID: Force Entry Logic FAILED!")

if __name__ == "__main__":
    test_force_entry()
