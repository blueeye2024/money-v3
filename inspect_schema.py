from backend.db import get_connection

def inspect_table(table_name):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print(f"--- Schema of {table_name} ---")
            cursor.execute(f"DESCRIBE {table_name}")
            rows = cursor.fetchall()
            for row in rows:
                print(row)
    except Exception as e:
        print(f"Error inspecting {table_name}: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_table("managed_stocks")
    print("\n")
    inspect_table("market_indices")
