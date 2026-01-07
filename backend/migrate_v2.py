import pymysql
import db
import os

def migrate():
    print("Starting V2 Schema Migration...")
    conn = db.get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Check buy_stock columns
            print("Checking buy_stock...")
            try:
                cursor.execute("SELECT final_buy_yn FROM buy_stock LIMIT 1")
            except Exception as e:
                print("Adding final_buy_yn column to buy_stock...")
                cursor.execute("ALTER TABLE buy_stock ADD COLUMN final_buy_yn CHAR(1) DEFAULT 'N'")
            
            try:
                cursor.execute("SELECT real_buy_yn FROM buy_stock LIMIT 1")
            except:
                print("Adding real_buy_yn column to buy_stock...")
                cursor.execute("ALTER TABLE buy_stock ADD COLUMN real_buy_yn CHAR(1) DEFAULT 'N'")
                cursor.execute("ALTER TABLE buy_stock ADD COLUMN real_buy_price DECIMAL(18,6)")
                cursor.execute("ALTER TABLE buy_stock ADD COLUMN real_buy_qn DECIMAL(10,2)")
                cursor.execute("ALTER TABLE buy_stock ADD COLUMN real_buy_dt DATETIME")

            # 2. Check sell_stock columns
            print("Checking sell_stock...")
            try:
                cursor.execute("SELECT close_yn FROM sell_stock LIMIT 1")
            except:
                print("Adding close_yn column to sell_stock...")
                cursor.execute("ALTER TABLE sell_stock ADD COLUMN close_yn CHAR(1) DEFAULT 'N'")

            try:
                cursor.execute("SELECT final_sell_yn FROM sell_stock LIMIT 1")
            except:
                print("Adding final_sell_yn column to sell_stock...")
                cursor.execute("ALTER TABLE sell_stock ADD COLUMN final_sell_yn CHAR(1) DEFAULT 'N'")
                cursor.execute("ALTER TABLE sell_stock ADD COLUMN final_sell_dt DATETIME")
                cursor.execute("ALTER TABLE sell_stock ADD COLUMN final_sell_price DECIMAL(18,6)")
            
            try:
                cursor.execute("SELECT real_hold_yn FROM sell_stock LIMIT 1")
            except:
                print("Adding real_hold_yn column to sell_stock...")
                cursor.execute("ALTER TABLE sell_stock ADD COLUMN real_hold_yn CHAR(1) DEFAULT 'N'")
                cursor.execute("ALTER TABLE sell_stock ADD COLUMN real_sell_avg_price DECIMAL(18,6)")
                cursor.execute("ALTER TABLE sell_stock ADD COLUMN real_sell_qn DECIMAL(10,2)")
                cursor.execute("ALTER TABLE sell_stock ADD COLUMN real_sell_dt DATETIME")

        conn.commit()
        print("Migration Completed Successfully.")
    except Exception as e:
        print(f"Migration Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
