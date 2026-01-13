
import pymysql
from db import get_connection

def inspect_table():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DESCRIBE buy_stock")
            rows = cursor.fetchall()
            print(f"{'Field':<20} {'Type':<20} {'Key':<10}")
            print("-" * 50)
            for row in rows:
                # row is tuple or dict depending on cursor. 
                # DESCRIBE returns fields: Field, Type, Null, Key, Default, Extra
                # If tuple: 0=Field
                if isinstance(row, dict):
                    print(f"{row['Field']:<20} {row['Type']:<20} {row['Key']:<10}")
                else:
                    print(f"{row[0]:<20} {row[1]:<20} {row[3]:<10}")
                    
            print("\nContent Check:")
            cursor.execute("SELECT * FROM buy_stock LIMIT 1")
            row = cursor.fetchone()
            print(row)
            
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_table()
