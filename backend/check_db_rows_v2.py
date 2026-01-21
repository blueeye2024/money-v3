import pymysql
import os
from datetime import datetime

# Load/Hardcode DB credentials (from db.py or env)
# Assuming standard user 'blue' or similar. 
# Better: import db from backend.
import sys
sys.path.append('/home/blue/blue/my_project/money/backend')
from db import get_connection

def check_rows():
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # soxl_candle_data (Legacy table) - Lowercase, separate columns
    # candle_date (YYYYMMDD), hour, minute
    
    table_name = "soxl_candle_data"
    sql = f"SELECT hour, minute, close_price FROM {table_name} ORDER BY candle_date DESC, hour DESC, minute DESC LIMIT 5" 
    
    try:
        cursor.execute(sql)
        res = cursor.fetchone()
        print(f"{table_name} (Today 20260121, Hour >= 10): {res}")
    except Exception as e:
        print(f"Error querying {table_name}: {e}")
    
    # market_candles (New table)
    # timestamp is datetime.
    sql2 = "SELECT count(*) as cnt, min(timestamp) as first, max(timestamp) as last FROM market_candles WHERE ticker='SOXL' and timestamp > '2026-01-21 00:00:00'" 
    try:
        cursor.execute(sql2)
        res2 = cursor.fetchone()
        print(f"market_candles (Today UTC > 00:00): {res2}")
    except Exception as e:
        print(f"Error querying market_candles: {e}")
    
    conn.close()

if __name__ == "__main__":
    check_rows()
