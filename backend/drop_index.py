import pymysql
from db import get_connection

def drop_unique_index():
    print("Dropping unique index from market_indicators_log...")
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check if index exists
            try:
                cursor.execute("DROP INDEX idx_ticker_unique ON market_indicators_log")
                print("Dropped 'idx_ticker_unique'.")
            except Exception as e:
                print(f"Could not drop index (might not exist): {e}")
                
            conn.commit()
            print("Cleanup completed.")
            
    except Exception as e:
        print(f"Cleanup Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    drop_unique_index()
