
import sys
import os
from datetime import datetime

# 백엔드 경로 추가
sys.path.append('/home/blue/blue/my_project/money/backend')

from db import get_connection

def insert_data():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # SOXL Data (Upsert)
            sql_soxl = """
                INSERT INTO market_indicators_log 
                (ticker, candle_time, rsi_14, vol_ratio, atr, pivot_r1, created_at)
                VALUES (%s, NOW(), %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                rsi_14 = VALUES(rsi_14),
                vol_ratio = VALUES(vol_ratio),
                atr = VALUES(atr),
                pivot_r1 = VALUES(pivot_r1),
                created_at = NOW(),
                candle_time = NOW()
            """
            cursor.execute(sql_soxl, ('SOXL', 65.5, 1.2, 0.45, 45.20))
            
            # SOXS Data (Upsert)
            sql_soxs = """
                INSERT INTO market_indicators_log 
                (ticker, candle_time, rsi_14, vol_ratio, atr, pivot_r1, created_at)
                VALUES (%s, NOW(), %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                rsi_14 = VALUES(rsi_14),
                vol_ratio = VALUES(vol_ratio),
                atr = VALUES(atr),
                pivot_r1 = VALUES(pivot_r1),
                created_at = NOW(),
                candle_time = NOW()
            """
            cursor.execute(sql_soxs, ('SOXS', 34.2, 0.8, 0.38, 18.50))
            
            conn.commit()
            print("Successfully inserted test data for SOXL and SOXS.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    insert_data()
