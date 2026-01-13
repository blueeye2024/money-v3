
import pymysql

DB_CONFIG = {
    "host": "114.108.180.228",
    "port": 3306,
    "user": "blueeye",
    "password": "blueeye0037!",
    "database": "mywork_01",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

def get_connection():
    return pymysql.connect(**DB_CONFIG)

def dump_schema():
    conn = get_connection()
    try:
        cur = conn.cursor()
        for table in ['buy_stock', 'sell_stock']:
            print(f"\n--- Table: {table} ---")
            cur.execute(f"DESC {table}")
            rows = cur.fetchall()
            for row in rows:
                print(f"{row['Field']} ({row['Type']}) Default: {row['Default']}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    dump_schema()
