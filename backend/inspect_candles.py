from db import get_connection

def check_candles():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check last 10 30m candles for SOXL
            sql = """
                SELECT candle_date, hour, minute, close_price, volume, is_30m 
                FROM soxl_candle_data 
                WHERE is_30m = 'Y' 
                ORDER BY candle_date DESC, hour DESC, minute DESC 
                LIMIT 10
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            print("Recent SOXL 30m Candles:")
            for r in rows:
                print(r)
    finally:
        conn.close()

if __name__ == "__main__":
    check_candles()
