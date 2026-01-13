import pymysql
import json

DB_CONFIG = {
    "host": "114.108.180.228",
    "port": 3306,
    "user": "blueeye",
    "password": "blueeye0037!",
    "database": "mywork_01",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

def check():
    conn = pymysql.connect(**DB_CONFIG)
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM soxs_candle_data ORDER BY candle_date DESC, hour DESC, minute DESC LIMIT 5")
        rows = cursor.fetchall()
        print(json.dumps(rows, default=str, indent=2))
        
        cursor.execute("SELECT COUNT(*) as cnt FROM soxs_candle_data")
        print(cursor.fetchone())
    conn.close()

if __name__ == "__main__":
    check()
