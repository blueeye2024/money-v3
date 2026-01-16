
import pymysql
import os
import sys

# Add backend directory to path to import db config if needed, or just connect directly.
# Using direct connection for simplicity as I know credentials.

DB_HOST = "114.108.180.228"
DB_USER = "blueeye"
DB_PASS = "blueeye0037!" 
DB_NAME = "mywork_01"

def add_column():
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            db=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        with conn.cursor() as cursor:
            # Check if column exists
            cursor.execute("DESCRIBE market_events")
            columns = [col['Field'] for col in cursor.fetchall()]
            
            if 'event_time' not in columns:
                print("Adding event_time column...")
                sql = "ALTER TABLE market_events ADD COLUMN event_time TIME AFTER event_date"
                cursor.execute(sql)
                conn.commit()
                print("Column added successfully.")
            else:
                print("Column event_time already exists.")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

if __name__ == "__main__":
    add_column()
