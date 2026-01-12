import pymysql
from db import get_connection

def migrate_macd():
    print("Starting Migration: Adding MACD columns...")
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Add columns to Snapshot table
            print("Updating market_indicators_snapshot...")
            try:
                cursor.execute("ALTER TABLE market_indicators_snapshot ADD COLUMN macd DECIMAL(10, 4) AFTER pivot_r1")
                cursor.execute("ALTER TABLE market_indicators_snapshot ADD COLUMN macd_sig DECIMAL(10, 4) AFTER macd")
                print("Added MACD columns to snapshot.")
            except Exception as e:
                print(f"Snapshot update skipped (maybe exists): {e}")

            # 2. Add columns to History table
            print("Updating market_indicators_history...")
            try:
                cursor.execute("ALTER TABLE market_indicators_history ADD COLUMN macd DECIMAL(10, 4) AFTER pivot_r1")
                cursor.execute("ALTER TABLE market_indicators_history ADD COLUMN macd_sig DECIMAL(10, 4) AFTER macd")
                print("Added MACD columns to history.")
            except Exception as e:
                print(f"History update skipped (maybe exists): {e}")

            conn.commit()
            print("Migration MACD Completed.")

    except Exception as e:
        print(f"Migration Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_macd()
