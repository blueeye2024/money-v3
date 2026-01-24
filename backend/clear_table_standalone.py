import pymysql
from pymysql.cursors import DictCursor

# Connection Config from db.py
DB_CONFIG = {
    "host": "114.108.180.228",
    "port": 3306,
    "user": "blueeye",
    "password": "blueeye0037!",
    "database": "mywork_01",
    "charset": "utf8mb4",
    "cursorclass": DictCursor
}

def clear_trade_history():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Connected to database.")
        
        cursor.execute("TRUNCATE TABLE trade_history")
        conn.commit()
        print("Successfully truncated trade_history table.")
        
        # Verify
        cursor.execute("SELECT count(*) as cnt FROM trade_history")
        res = cursor.fetchone()
        print(f"Row count after truncate: {res['cnt']}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clear_trade_history()
