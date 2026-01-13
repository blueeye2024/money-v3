import sys
sys.path.append('/home/blue/blue/my_project/money/backend')
import pandas as pd
import pandas_ta as ta
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

def load_real_data():
    conn = pymysql.connect(**DB_CONFIG)
    sql = "SELECT * FROM soxs_candle_data WHERE is_30m='Y' ORDER BY candle_date DESC, hour DESC, minute DESC LIMIT 60"
    df = pd.read_sql(sql, conn)
    conn.close()
    
    if not df.empty:
        df = df.iloc[::-1].reset_index(drop=True)
        # Convert Decimal to float
        df['Close'] = df['close_price'].astype(float)
        return df
    return None

def test():
    print("Testing SMA with Real SOXS Data...")
    df = load_real_data()
    if df is not None:
        try:
            # Check for generic object types
            print(f"Close Dtype: {df['Close'].dtype}")
            
            # Should work if dtype is float64
            sma10 = ta.sma(df['Close'], length=10)
            print(f"SMA 10 Last: {sma10.iloc[-1]}")
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test()
