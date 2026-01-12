
import pymysql
import os

# DB Config directly from db.py
DB_CONFIG = {
    "host": "114.108.180.228",
    "port": 3306,
    "user": "blueeye",
    "password": "blueeye0037!",
    "database": "mywork_01",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

def migrate_db():
    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        TARGET_TABLE = "trade_journal"

        print(f"Starting DB Migration for '{TARGET_TABLE}' table...")

        # Check if 'screenshot' column exists and add it
        cursor.execute(f"DESCRIBE {TARGET_TABLE}")
        columns = [row['Field'] for row in cursor.fetchall()]

        if 'screenshot' not in columns:
            print("Adding 'screenshot' column...")
            # Use LONGTEXT for base64 images
            cursor.execute(f"ALTER TABLE {TARGET_TABLE} ADD COLUMN screenshot LONGTEXT COMMENT '차트 스크린샷 (Base64)'")
            print("'screenshot' column added.")
        else:
            print("'screenshot' column already exists. Skipping.")
        
        conn.commit()
        print("DB Migration completed successfully.")

    except Exception as e:
        print(f"Error during migration: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_db()
