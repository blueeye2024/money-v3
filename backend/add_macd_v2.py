
import pymysql

# Connection Config from db.py
DB_CONFIG = {
    "host": "114.108.180.228",
    "port": 3306,
    "user": "blueeye",
    "password": "blueeye0037!",
    "database": "mywork_01",
    "charset": "utf8mb4"
}

def migrate():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            # Check if column exists
            cursor.execute("SHOW COLUMNS FROM market_indicators_log LIKE 'macd'")
            if not cursor.fetchone():
                print("Adding 'macd' column...")
                cursor.execute("ALTER TABLE market_indicators_log ADD COLUMN macd DECIMAL(10, 4) DEFAULT NULL AFTER atr")
                conn.commit()
                print("✅ Column 'macd' added.")
            else:
                print("ℹ️ Column 'macd' already exists.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
