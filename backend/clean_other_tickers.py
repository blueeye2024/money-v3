import sys
import os
sys.path.append(os.getcwd())
from db import get_connection

def clean_tables():
    conn = get_connection()
    tickers = ['soxs', 'upro']
    with conn.cursor() as cur:
        for t in tickers:
            print(f"Cleaning {t}...")
            cur.execute(f"TRUNCATE TABLE {t}_candle_data")
    conn.commit()
    conn.close()
    print("Clean Complete.")

if __name__ == "__main__":
    clean_tables()
