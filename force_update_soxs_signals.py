import pymysql
import datetime
from backend.db import get_connection

def force_update():
    print("Force Updating SOXS Signals to Level 3...")
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check Active Record
            cursor.execute("SELECT manage_id FROM buy_stock WHERE ticker='SOXS' AND final_buy_yn='N'")
            row = cursor.fetchone()
            if not row:
                print("No active SOXS record found.")
                return

            manage_id = row['manage_id']
            print(f"Updating Record: {manage_id}")

            # Update to Signal 3 (All Y)
            sql = """
                UPDATE buy_stock
                SET buy_sig1_yn = 'Y', buy_sig2_yn = 'Y', buy_sig3_yn = 'Y',
                    buy_sig1_dt = NOW(), buy_sig2_dt = NOW(), buy_sig3_dt = NOW(),
                    row_dt = NOW()
                WHERE manage_id = %s
            """
            cursor.execute(sql, (manage_id,))
            print("Successfully updated SOXS signals to 3rd Stage.")
            
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    force_update()
