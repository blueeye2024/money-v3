import pymysql
import json
from db import get_connection

def check_status():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check SOXL Levels
            cursor.execute("SELECT ticker, level_type, stage, price, is_active, triggered FROM manual_price_levels WHERE ticker IN ('SOXL', 'SOXS')")
            rows = cursor.fetchall()
            print("--- Manual Price Levels ---")
            for r in rows:
                print(r)
                
            # Check if there are any recent system triggers
            # (If I knew the table, but sticking to manual levels for now)
            
    finally:
        conn.close()

if __name__ == "__main__":
    check_status()
