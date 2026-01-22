from backend.db import get_connection

def check_nulls():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM market_candles WHERE close_price IS NULL")
            count = cursor.fetchone()[0]
            print(f"Null close_price count: {count}")
            
            cursor.execute("SELECT count(*) FROM managed_stocks")
            print(f"Managed stocks count: {cursor.fetchone()[0]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_nulls()
