
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "money")

def check_latest_time():
    conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cursor:
            # Check SOXL 5m candles
            sql = "SELECT candle_date, hour, minute, close_price FROM soxl_candle_data ORDER BY candle_date DESC, hour DESC, minute DESC LIMIT 5"
            cursor.execute(sql)
            rows = cursor.fetchall()
            print("--- Latest SOXL Data ---")
            for r in rows:
                print(r)
    finally:
        conn.close()

if __name__ == "__main__":
    check_latest_time()
