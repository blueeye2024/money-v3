
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
        
        # NOTE: Using 'trade_journal' based on previous checks
        TARGET_TABLE = "trade_journal"

        print(f"Starting DB Migration for '{TARGET_TABLE}' table...")

        # Check if 'prediction_score' column exists and add it
        cursor.execute(f"DESCRIBE {TARGET_TABLE}")
        columns = [row['Field'] for row in cursor.fetchall()]

        if 'prediction_score' not in columns:
            print("Adding 'prediction_score' column...")
            cursor.execute(f"ALTER TABLE {TARGET_TABLE} ADD COLUMN prediction_score VARCHAR(50) COMMENT '예측지수' AFTER market_condition")
            print("'prediction_score' column added.")
        else:
            print("'prediction_score' column already exists. Skipping.")
        
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
