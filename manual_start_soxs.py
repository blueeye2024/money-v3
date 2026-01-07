import pymysql
import datetime
from backend.db import get_connection

def manual_start():
    print("Manually Starting SOXS Trade Cycle...")
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Generate New Manage ID
            now = datetime.datetime.now()
            manage_id = f"SOXS{now.strftime('%Y%m%d_%H%M')}"
            print(f"Generated Manage ID: {manage_id}")

            # 2. Insert into buy_stock
            sql = """
                INSERT INTO buy_stock (ticker, manage_id, row_dt, buy_sig1_yn, final_buy_yn, real_buy_yn)
                VALUES ('SOXS', %s, NOW(), 'Y', 'N', 'N')
            """
            cursor.execute(sql, (manage_id,))
            print("Inserted new active record into buy_stock.")
            
        conn.commit()
        print("Success! Refresh the dashboard.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    manual_start()
