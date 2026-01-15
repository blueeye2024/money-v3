import os
import sys
import pymysql.cursors
from db import get_connection

def check_soxs():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM sell_stock WHERE ticker='SOXS'")
            row = cur.fetchone()
            print("--- SOXS SELL_STOCK RECORD ---")
            for k, v in row.items():
                print(f"{k}: {v}")
                
            print("\n--- RECENT SIGNAL HISTORY (Last 5) ---")
            cur.execute("SELECT id, signal_type, signal_reason, signal_time, created_at FROM signal_history WHERE ticker='SOXS' ORDER BY id DESC LIMIT 5")
            hist = cur.fetchall()
            for h in hist:
                print(h)
    finally:
        conn.close()

if __name__ == "__main__":
    check_soxs()
