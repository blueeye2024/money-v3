from db import get_connection

def add_manual_flags():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. buy_stock columns
            buy_cols = ['is_manual_buy1', 'is_manual_buy2', 'is_manual_buy3']
            for col in buy_cols:
                try:
                    print(f"Adding {col} to buy_stock...")
                    cursor.execute(f"ALTER TABLE buy_stock ADD COLUMN {col} CHAR(1) DEFAULT 'N'")
                except Exception as e:
                    print(f"Skipped {col}: {e}")

            # 2. sell_stock columns
            sell_cols = ['is_manual_sell1', 'is_manual_sell2', 'is_manual_sell3']
            for col in sell_cols:
                try:
                    print(f"Adding {col} to sell_stock...")
                    cursor.execute(f"ALTER TABLE sell_stock ADD COLUMN {col} CHAR(1) DEFAULT 'N'")
                except Exception as e:
                    print(f"Skipped {col}: {e}")

        conn.commit()
        print("Migration Completed Successfully.")
    except Exception as e:
        print(f"Migration Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_manual_flags()
