import sys
import os
import json
import asyncio
sys.path.append(os.getcwd())
from db import get_connection

async def main():
    print("Verifying Data Quality Fix...")
    
    # 1. Trigger Calc (via direct call or curl)
    # Use curl for end-to-end
    print("Triggering Batch Calc...")
    cmd = 'curl -s -X POST "http://localhost:9100/api/lab/calculate?period=30m&ticker=SOXL&offset=0&limit=10&only_missing=False"'
    os.system(cmd)
    
    # 2. Check DB
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, total_score, change_pct, score_rsi, score_macd FROM lab_data_30m WHERE ticker='SOXL' ORDER BY candle_time ASC LIMIT 5")
            rows = cursor.fetchall()
            print("\n\nDB Data Check:")
            for r in rows:
                print(f"ID={r['id']}, Score={r['total_score']}, Chg={r['change_pct']}%, RSI_S={r['score_rsi']}, MACD_S={r['score_macd']}")
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(main())
