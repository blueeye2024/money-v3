from backend.db import get_holdings, get_connection

print("--- Testing get_holdings ---")
try:
    data = get_holdings()
    print(f"Result Type: {type(data)}")
    print(f"Result Length: {len(data)}")
    print(f"Data: {data}")
except Exception as e:
    print(f"Error: {e}")

print("--- Testing Direct Query ---")
conn = get_connection()
try:
    with conn.cursor() as cur:
        cur.execute("SELECT ticker, quantity FROM managed_stocks WHERE quantity > 0")
        print(f"Direct Query: {cur.fetchall()}")
finally:
    conn.close()
