from db import get_connection
import traceback

def check_candles():
    conn = None
    try:
        conn = get_connection()
        print("DB Connection Successful")
        with conn.cursor() as cursor:
            # Check if table exists
            cursor.execute("SHOW TABLES LIKE 'soxl_candle_data'")
            if not cursor.fetchone():
                print("Table soxl_candle_data DOES NOT EXIST")
                return

            cursor.execute("SELECT count(*) FROM soxl_candle_data")
            row = cursor.fetchone()
            print(f"Total rows: {row}")

            cursor.execute("SELECT count(*) FROM soxl_candle_data WHERE is_30m IS NULL OR is_30m != 'Y'")
            c5m = cursor.fetchone()
            print(f"5m rows: {c5m}")

            cursor.execute("SELECT count(*) FROM soxl_candle_data WHERE is_30m = 'Y'")
            c30m = cursor.fetchone()
            print(f"30m rows: {c30m}")
            
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_candles()
