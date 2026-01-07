import pymysql
from backend.db import get_connection

def diagnose_soxs():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("--- SOXS BUY_STOCK (Active Only) ---")
            cursor.execute("SELECT idx, manage_id, buy_sig1_yn, final_buy_yn, row_dt FROM buy_stock WHERE ticker='SOXS' AND final_buy_yn='N'")
            rows = cursor.fetchall()
            for row in rows:
                print(row)

            print("\n--- SOXS BUY_STOCK (All Recent 5) ---")
            cursor.execute("SELECT idx, manage_id, buy_sig1_yn, final_buy_yn, row_dt FROM buy_stock WHERE ticker='SOXS' ORDER BY idx DESC LIMIT 5")
            rows = cursor.fetchall()
            for row in rows:
                print(row)

            print("\n--- SOXS SELL_STOCK (Active Only) ---")
            cursor.execute("SELECT idx, manage_id, close_yn, final_sell_yn, row_dt FROM sell_stock WHERE ticker='SOXS' AND close_yn='N'")
            rows = cursor.fetchall()
            for row in rows:
                print(row)
                
    except Exception as e:
        print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    diagnose_soxs()
