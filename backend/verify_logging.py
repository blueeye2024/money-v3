import pymysql
from db import get_connection

def verify():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT id, ticker, score, evaluation, left(strategy_comment, 50) as cmt, v2_state, created_at FROM market_indicators_log ORDER BY id DESC LIMIT 5"
            cursor.execute(sql)
            rows = cursor.fetchall()
            print(f"Found {len(rows)} logs:")
            for r in rows:
                print(r)
    finally:
        conn.close()

if __name__ == "__main__":
    verify()
