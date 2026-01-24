from db import get_connection

def migrate_add_macd():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check if column exists
            cursor.execute("SHOW COLUMNS FROM market_indicators_log LIKE 'macd'")
            if not cursor.fetchone():
                print("Adding 'macd' column to market_indicators_log...")
                cursor.execute("ALTER TABLE market_indicators_log ADD COLUMN macd DECIMAL(10, 4) DEFAULT NULL AFTER atr")
                conn.commit()
                print("✅ Column 'macd' added successfully.")
            else:
                print("ℹ️ Column 'macd' already exists.")
                
    except Exception as e:
        print(f"Migration Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_add_macd()
