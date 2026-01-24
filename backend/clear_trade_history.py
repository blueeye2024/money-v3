from db import get_connection

def clear_trade_history():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("TRUNCATE TABLE trade_history")
        conn.commit()
        print("Successfully truncated trade_history table.")
    except Exception as e:
        print(f"Error truncating table: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    clear_trade_history()
