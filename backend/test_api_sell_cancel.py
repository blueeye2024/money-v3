
import requests
import pymysql
import json
import time

DB_CONFIG = {
    "host": "114.108.180.228",
    "port": 3306,
    "user": "blueeye",
    "password": "blueeye0037!",
    "database": "mywork_01",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

def get_connection():
    return pymysql.connect(**DB_CONFIG)

def check_db(ticker):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT buy_sig1_yn, is_manual_buy1, final_buy_yn FROM buy_stock WHERE ticker=%s", (ticker,))
        buy = cur.fetchone()
        
        cur.execute("SELECT sell_sig1_yn, is_manual_sell1 FROM sell_stock WHERE ticker=%s", (ticker,))
        sell = cur.fetchone()
        
        return buy, sell
    finally:
        conn.close()

def run_test():
    ticker = 'TEST_API'
    
    # 1. Setup DB State (Manually to ensure clean slate)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM buy_stock WHERE ticker=%s", (ticker,))
        cur.execute("DELETE FROM sell_stock WHERE ticker=%s", (ticker,))
        
        # Create Buy (Finished)
        cur.execute("INSERT INTO buy_stock (ticker, buy_sig1_yn, final_buy_yn, is_manual_buy1) VALUES (%s, 'Y', 'Y', 'Y')", (ticker,))
        # Create Sell (Active Signal 1)
        cur.execute("INSERT INTO sell_stock (ticker, sell_sig1_yn, is_manual_sell1) VALUES (%s, 'Y', 'Y')", (ticker,))
        conn.commit()
    finally:
        conn.close()

    print("--- Initial DB State ---")
    b, s = check_db(ticker)
    print(f"Buy Stock: {b}")
    print(f"Sell Stock: {s}")

    # 2. Call API to Cancel SELL Signal 1
    url = "http://localhost:8000/api/v2/manual-signal"
    payload = {
        "ticker": ticker,
        "signal_key": "sell1",
        "price": 0,
        "status": "N",
        "manage_id": "TEST_ID"
    }
    
    print("\n--- Calling API (sell1 -> N) ---")
    try:
        res = requests.post(url, json=payload)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
    except Exception as e:
        print(f"Request Error: {e}")
        return

    # 3. Check Result
    print("\n--- Final DB State ---")
    b_new, s_new = check_db(ticker)
    print(f"Buy Stock: {b_new}")
    print(f"Sell Stock: {s_new}")
    
    if s_new['sell_sig1_yn'] == 'N' and s_new['is_manual_sell1'] == 'N':
        print("\n✅ SUCCESS: Sell Stock Updated Correctly.")
        if b_new['buy_sig1_yn'] == 'Y':
             print("✅ VERIFIED: Buy Stock UNTOUCHED.")
        else:
             print("❌ FAIL: Buy Stock changed unexpectedly!")
    else:
        print("\n❌ FAIL: Sell Stock NOT Updated!")
        if b_new['buy_sig1_yn'] == 'N':
            print("🚨 CRITICAL: Buy Stock was updated instead! (CROSS WRITE BUG)")

if __name__ == "__main__":
    run_test()
