
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

def add_columns():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        print("Adding manual_target columns to sell_stock...")
        
        cols = [
            "manual_target_sell1 DECIMAL(10,2) DEFAULT 0",
            "manual_target_sell2 DECIMAL(10,2) DEFAULT 0",
            "manual_target_sell3 DECIMAL(10,2) DEFAULT 0"
        ]
        
        for col in cols:
            try:
                cur.execute(f"ALTER TABLE sell_stock ADD COLUMN {col}")
                print(f"Added: {col}")
            except Exception as e:
                print(f"Skipped (maybe exists): {col} - {e}")
        
        conn.commit()
        print("Done.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_columns()
