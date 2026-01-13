
import pymysql
from db import get_connection

def apply_schema_fix():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Check buy_stock columns
            cursor.execute("DESCRIBE buy_stock")
            buy_cols = [row['Field'] for row in cursor.fetchall()]
            
            print(f"Current buy_stock cols: {buy_cols}")
            
            if 'manage_id' not in buy_cols:
                print("Adding manage_id to buy_stock...")
                cursor.execute("ALTER TABLE buy_stock ADD COLUMN manage_id VARCHAR(50)")
            
            if 'idx' not in buy_cols:
                print("Adding idx to buy_stock...")
                cursor.execute("ALTER TABLE buy_stock ADD COLUMN idx INT AUTO_INCREMENT UNIQUE")
                
            # 2. Check sell_stock columns
            cursor.execute("DESCRIBE sell_stock")
            sell_cols = [row['Field'] for row in cursor.fetchall()]
            print(f"Current sell_stock cols: {sell_cols}")

            if 'manage_id' not in sell_cols:
                print("Adding manage_id to sell_stock...")
                cursor.execute("ALTER TABLE sell_stock ADD COLUMN manage_id VARCHAR(50)")
                
            if 'idx' not in sell_cols:
                print("Adding idx to sell_stock...")
                cursor.execute("ALTER TABLE sell_stock ADD COLUMN idx INT AUTO_INCREMENT UNIQUE")
                
            conn.commit()
            print("✅ Schema Fix Applied Successfully!")
            
    except Exception as e:
        print(f"Schema Fix Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    apply_schema_fix()
