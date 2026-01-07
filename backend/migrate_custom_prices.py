import pymysql
import os
from db import get_connection

def add_custom_price_columns():
    conn = get_connection()
    if conn is None:
        print("❌ DB Connection Failed")
        return

    try:
        cur = conn.cursor()
        
        # 1. Add target_box_price to buy_stock
        print("Adding target_box_price to buy_stock...")
        try:
            cur.execute("""
                ALTER TABLE buy_stock 
                ADD COLUMN target_box_price DECIMAL(18,6) DEFAULT NULL 
                AFTER buy_sig2_price
            """)
            print("✅ Added target_box_price")
        except pymysql.er.OperationalError as e:
            if "Duplicate column" in str(e):
                print("⚠️ target_box_price already exists")
            else:
                raise e

        # 2. Add target_stop_price to sell_stock
        print("Adding target_stop_price to sell_stock...")
        try:
            cur.execute("""
                ALTER TABLE sell_stock 
                ADD COLUMN target_stop_price DECIMAL(18,6) DEFAULT NULL 
                AFTER sell_sig2_price
            """)
            print("✅ Added target_stop_price")
        except pymysql.er.OperationalError as e:
            if "Duplicate column" in str(e):
                print("⚠️ target_stop_price already exists")
            else:
                raise e
        
        conn.commit()
        print("✨ Migration Complete")

    except Exception as e:
        print(f"❌ Migration Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_custom_price_columns()
