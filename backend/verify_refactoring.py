import pymysql
from db import get_connection

def verify():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("--- SNAPSHOT TABLE (Expected: 1 row per ticker) ---")
            cursor.execute("SELECT ticker, score, evaluation, updated_at FROM market_indicators_snapshot")
            snaps = cursor.fetchall()
            print(f"Total Rows: {len(snaps)}")
            for s in snaps:
                print(f"  📍 {s['ticker']}: {s['score']} ({s['evaluation']}) @ {s['updated_at']}")
            
            print("\n--- HISTORY TABLE (Expected: > Snapshot count) ---")
            cursor.execute("SELECT count(*) as cnt FROM market_indicators_history")
            hist_cnt = cursor.fetchone()['cnt']
            print(f"Total History Count: {hist_cnt}")
            
            cursor.execute("SELECT ticker, score, created_at FROM market_indicators_history ORDER BY id DESC LIMIT 3")
            print("Latest 3 History Records:")
            for h in cursor.fetchall():
                print(f"  📜 {h['ticker']}: {h['score']} @ {h['created_at']}")
                
    except Exception as e:
        print(f"Verification Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    verify()
