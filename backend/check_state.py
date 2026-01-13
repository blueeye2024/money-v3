
import pymysql
import json

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

def check_state():
    conn = get_connection()
    try:
        cur = conn.cursor()
        print("\n--- SOXS State ---")
        cur.execute("SELECT buy_sig1_yn, final_buy_yn, is_manual_buy1 FROM buy_stock WHERE ticker='SOXS'")
        print("Buy:", cur.fetchone())
        cur.execute("SELECT sell_sig1_yn, final_sell_yn, is_manual_sell1 FROM sell_stock WHERE ticker='SOXS'")
        print("Sell:", cur.fetchone())

        print("\n--- SOXL State ---")
        cur.execute("SELECT buy_sig1_yn, final_buy_yn, is_manual_buy1 FROM buy_stock WHERE ticker='SOXL'")
        print("Buy:", cur.fetchone())
        cur.execute("SELECT sell_sig1_yn, final_sell_yn, is_manual_sell1 FROM sell_stock WHERE ticker='SOXL'")
        print("Sell:", cur.fetchone())

    finally:
        conn.close()

if __name__ == "__main__":
    check_state()
