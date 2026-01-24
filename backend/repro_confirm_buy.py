
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import get_connection, confirm_v2_buy

def test_confirm_buy():
    ticker = 'SOXL'
    
    # 1. Reset State
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("UPDATE buy_stock SET buy_sig1_yn='N', buy_sig2_yn='N', buy_sig3_yn='N', final_buy_yn='N', real_buy_yn='N' WHERE ticker=%s", (ticker,))
    conn.commit()
    conn.close()
    
    # 2. Call confirm_v2_buy
    print("Calling confirm_v2_buy...")
    confirm_v2_buy(ticker, 100.0, 10)
    
    # 3. Check State
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM buy_stock WHERE ticker=%s", (ticker,))
        row = cursor.fetchone()
        
    print(f"Result for {ticker}:")
    print(f"  real_buy_yn: {row['real_buy_yn']}")
    print(f"  buy_sig1_yn: {row['buy_sig1_yn']}")
    print(f"  buy_sig2_yn: {row['buy_sig2_yn']}")
    print(f"  buy_sig3_yn: {row['buy_sig3_yn']}")
    
    if row['buy_sig1_yn'] == 'Y':
        print("FAIL: buy_sig1_yn is Y (Should be N)")
    else:
        print("PASS: buy_sig1_yn is N")

if __name__ == "__main__":
    test_confirm_buy()
