import sys
import os
sys.path.append(os.getcwd())
from db import get_connection

conn = get_connection()
try:
    with conn.cursor() as cursor:
        cursor.execute("UPDATE lab_data_30m SET total_score=0 WHERE id IN (1, 2) AND ticker='SOXL'")
    conn.commit()
    print("Reset scores for ID 1, 2")
finally:
    conn.close()
