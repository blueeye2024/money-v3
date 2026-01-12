
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
        
        print("Starting DB Migration for 'journal' table...")

        # 1. Check if 'emotion' column exists and drop it
        cursor.execute("DESCRIBE journal")
        columns = [row['Field'] for row in cursor.fetchall()]

        if 'emotion' in columns:
            print("Removing 'emotion' column...")
            cursor.execute("ALTER TABLE journal DROP COLUMN emotion")
            print("'emotion' column removed.")
        else:
            print("'emotion' column does not exist. Skipping.")

        # 2. Check if 'total_assets' column exists and add it
        if 'total_assets' not in columns:
            print("Adding 'total_assets' column...")
            cursor.execute("ALTER TABLE journal ADD COLUMN total_assets DECIMAL(15, 2) COMMENT '총 자산 (USD)' AFTER ticker")
            print("'total_assets' column added.")
        else:
            print("'total_assets' column already exists. Skipping.")
        
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
