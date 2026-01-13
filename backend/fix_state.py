
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

def fix_state():
    conn = get_connection()
    try:
        cur = conn.cursor()
        print("Restoring SOXS to Holding State...")
        
        # 1. Ensure Buy is Finalized
        cur.execute("UPDATE buy_stock SET final_buy_yn='Y', buy_sig1_yn='Y', buy_sig2_yn='Y', buy_sig3_yn='Y' WHERE ticker='SOXS'")
        
        # 2. Ensure Sell is Active (Not Finalized)
        # Also clean up sell signals to test fresh
        cur.execute("UPDATE sell_stock SET final_sell_yn='N', close_yn='N', sell_sig1_yn='N', sell_sig2_yn='N', sell_sig3_yn='N', is_manual_sell1='N', is_manual_sell2='N', is_manual_sell3='N' WHERE ticker='SOXS'")
        
        conn.commit()
        print("✅ SOXS State Restored: Holding (Buy=Y, Sell=N)")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_state()
