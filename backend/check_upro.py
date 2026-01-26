
import pymysql
from db import get_connection

def check_upro():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM managed_stocks WHERE ticker = 'UPRO'")
            result = cursor.fetchone()
            if result:
                print(f"✅ UPRO found in managed_stocks: {result}")
            else:
                print("❌ UPRO NOT found in managed_stocks")
                
                # Add if missing
                print("Adding UPRO...")
                cursor.execute("""
                    INSERT INTO managed_stocks (ticker, stock_name, is_active, strategy_type)
                    VALUES ('UPRO', 'UltraPro S&P500', 1, 'basic')
                """)
                conn.commit()
                print("✅ UPRO added.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_upro()
