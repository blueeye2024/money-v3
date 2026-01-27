
import pymysql
from db import get_connection

def reset_data():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Signal History
            print("Truncating signal_history...")
            cursor.execute("TRUNCATE TABLE signal_history")
            
            # 2. System Trades
            print("Truncating system_trades...")
            cursor.execute("TRUNCATE TABLE system_trades")
            
            # 3. Buy/Sell Stock (Optional? User said 'Signal History' and 'System Trading Log'. 
            # Usually these are decoupled from current positions, but let's stick to the requested tables first 
            # to avoid deleting open positions unless requested.)
            # User said: "SOXL (BULL) Signal History, SOXS (BEAR) Signal History, System Trading Log 기존 데이터 삭제"
            # These map to signal_history and system_trades.
            
        conn.commit()
        print("✅ Data Reset Complete.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    reset_data()
