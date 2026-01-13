
import pymysql
import sys

# DB Config
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

def reset_soxs_buy_mode():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            ticker = 'SOXS'
            
            # Clear buy_stock active signals
            sql_buy = """
                UPDATE buy_stock 
                SET final_buy_yn='N', buy_sig1_yn='N', buy_sig2_yn='N', buy_sig3_yn='N',
                    is_manual_buy1='N', is_manual_buy2='N', is_manual_buy3='N'
                WHERE ticker=%s
            """
            cursor.execute(sql_buy, (ticker,))
            
            # Clear sell_stock
            sql_sell = "DELETE FROM sell_stock WHERE ticker=%s"
            cursor.execute(sql_sell, (ticker,))
            
            conn.commit()
            print("✅ SOXS state reset to BUY MODE (All Signals Cleared).")
            
    finally:
        conn.close()

if __name__ == "__main__":
    reset_soxs_buy_mode()
