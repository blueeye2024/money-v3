from db import get_connection

CORE = ["SOXL", "SOXS", "UPRO"]

def clean():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check current count
        cursor.execute("SELECT COUNT(*) FROM market_candles")
        before = cursor.fetchone()[0]
        print(f"Total candles before cleanup: {before}")
        
        # Delete non-core
        format_strings = ','.join(['%s'] * len(CORE))
        sql = f"DELETE FROM market_candles WHERE ticker NOT IN ({format_strings})"
        
        print(f"Keeping only: {CORE}")
        cursor.execute(sql, tuple(CORE))
        conn.commit()
        deleted = cursor.rowcount
        print(f"Deleted {deleted} rows.")
        
        # Check after count
        cursor.execute("SELECT COUNT(*) FROM market_candles")
        after = cursor.fetchone()[0]
        print(f"Total candles after cleanup: {after}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clean()
