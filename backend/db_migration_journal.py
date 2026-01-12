
import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path='/home/blue/blue/my_project/money/backend/.env')

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "blue")
DB_PASSWORD = os.getenv("DB_PASSWORD", "blueeye0037!")
DB_NAME = os.getenv("DB_NAME", "money_v3")

def migrate_db():
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
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
        
        # 3. Rename 'buy_reason' to 'memo' if requested? 
        # User asked to change TEXT in UI, but let's keep DB column name 'buy_reason' or 'note'
        # To avoid massive refactoring, we will map UI 'Memo' to DB 'buy_reason' for now, or we can rename.
        # User said "Change buy reason text to Memo". It's safer to just change the LABEL in UI.
        # But for 'total_assets', it needs a real column.

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
