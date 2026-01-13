
import pymysql
import sys
import time

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

def test_coupling():
    conn = get_connection()
    try:
        ticker = 'TEST'
        from db import manual_update_signal, delete_v2_record, get_v2_buy_status, get_v2_sell_status
        
        # 1. Clean Start
        print("1. Cleaning old test data...")
        delete_v2_record(ticker)
        
        # 2. Create Buy Signal 1 (Manual ON)
        print("2. Creating Buy Signal 1 (Manual)...")
        manual_update_signal(ticker, 'buy1', 100, 'Y')
        
        # 3. Create Sell Signal 1 (Manual ON)
        print("3. Creating Sell Signal 1 (Manual)...")
        manual_update_signal(ticker, 'sell1', 105, 'Y')
        
        # Verify both exist
        buy = get_v2_buy_status(ticker)
        sell = get_v2_sell_status(ticker)
        
        if not buy or not sell:
            print(f"❌ Setup Failed: Buy={bool(buy)}, Sell={bool(sell)}")
            return
            
        print("✅ Setup Complete: Buy=Y, Sell=Y")
        
        # 4. Cancel Buy Signal 1
        print("4. Cancelling Buy Signal 1 (status='N')...")
        manual_update_signal(ticker, 'buy1', 0, 'N')
        
        # 5. Check if Sell Signal Survived
        sell_after = get_v2_sell_status(ticker)
        buy_after = get_v2_buy_status(ticker)
        
        print(f"   Buy1 After: {buy_after.get('buy_sig1_yn')}")
        
        if sell_after and sell_after.get('sell_sig1_yn') == 'Y':
             print("✅ Sell Signal SURVIVED! (Decoupled)")
        else:
             print("❌ Sell Signal DISAPPEARED! (Coupled Bug Confirmed)")
             print(f"   Sell Record: {sell_after}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_coupling()
