from db import get_connection

def inspect_table():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DESCRIBE soxl_candle_data")
            rows = cursor.fetchall()
            print(f"Columns in soxl_candle_data:")
            for row in rows:
                print(row)
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_table()
