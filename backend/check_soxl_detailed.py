import pymysql
import pandas as pd
import pandas_ta as ta
import sys

# Add path for kis_api_v2
sys.path.append('/home/blue/blue/my_project/money/backend')

DB_CONFIG = {
    "host": "114.108.180.228",
    "port": 3306,
    "user": "blueeye",
    "password": "blueeye0037!",
    "database": "mywork_01",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

def check_soxl_signals():
    print(f"\n======== SOXL SIGNAL DIAGNOSIS ========")
    
    # 1. Check Real-time Price & Change from KIS
    try:
        from kis_api_v2 import kis_client
        # Force 'NYS'
        res = kis_client.get_price('SOXL', 'NYS')
        print(f"[KIS API] Current Price: {res.get('price')}")
        print(f"[KIS API] Daily Change: {res.get('rate')}% (Target: >= +2.0%)")
        
        step2_pass = res.get('rate', 0) >= 2.0
        print(f"👉 Step 2 (Box/Momentum) Status: {'✅ PASS' if step2_pass else '❌ FAIL'}")
        
    except Exception as e:
        print(f"[KIS Error] {e}")

    # 2. Check 30m Trend (Step 3: Gold Cross)
    try:
        conn = pymysql.connect(**DB_CONFIG)
        sql = "SELECT close_price FROM soxl_candle_data WHERE timeframe='30m' ORDER BY candle_date DESC, hour DESC, minute DESC LIMIT 60"
        df = pd.read_sql(sql, conn)
        conn.close()
        
        if not df.empty:
            df = df.iloc[::-1].reset_index(drop=True)
            df['Close'] = df['close_price'].astype(float)
            df['SMA10'] = ta.sma(df['Close'], 10)
            df['SMA30'] = ta.sma(df['Close'], 30)
            
            curr = df.iloc[-1]
            is_gold = curr['SMA10'] > curr['SMA30']
            
            print(f"\n[30m Trend Analysis]")
            print(f"Latest Close: {curr['Close']}")
            print(f"MA10: {curr['SMA10']:.2f} / MA30: {curr['SMA30']:.2f}")
            print(f"👉 Step 3 (Trend) Status: {'✅ PASS (Gold)' if is_gold else '❌ FAIL (Dead/Inverse)'}")
            
    except Exception as e:
        print(f"[DB Error] {e}")

if __name__ == "__main__":
    check_soxl_signals()
