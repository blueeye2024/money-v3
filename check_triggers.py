
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from db import get_connection

def check_triggers():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("Checking Triggers...")
            cursor.execute("SHOW TRIGGERS")
            triggers = cursor.fetchall()
            if not triggers:
                print("✅ No Triggers found.")
            else:
                for t in triggers:
                    print(f"⚠️ Trigger Found: {t}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_triggers()
