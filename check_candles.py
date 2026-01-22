from backend.db import get_connection

def check_candles():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM soxl_candle_data")
            total = cursor.fetchone()[0]
            print(f"Total rows: {total}")
            
            cursor.execute("SELECT count(*) FROM soxl_candle_data WHERE is_30m IS NULL OR is_30m != 'Y'")
            c5m = cursor.fetchone()[0]
            print(f"5m rows: {c5m}")

            cursor.execute("SELECT count(*) FROM soxl_candle_data WHERE is_30m = 'Y'")
            c30m = cursor.fetchone()[0]
            print(f"30m rows: {c30m}")
            
            cursor.execute("SELECT candle_date, hour, minute FROM soxl_candle_data ORDER BY candle_date DESC, hour DESC, minute DESC LIMIT 5")
            print("Latest 5 rows:")
            for r in cursor.fetchall():
                print(r)
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_candles()
