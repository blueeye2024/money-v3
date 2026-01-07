from backend.db import get_connection
import pymysql

def migrate():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Add columns to managed_stocks
            print("1. Adding columns to managed_stocks...")
            try:
                cur.execute("ALTER TABLE managed_stocks ADD COLUMN quantity INT DEFAULT 0")
                cur.execute("ALTER TABLE managed_stocks ADD COLUMN avg_price DECIMAL(15, 4) DEFAULT 0.0")
                cur.execute("ALTER TABLE managed_stocks ADD COLUMN currency VARCHAR(3) DEFAULT 'USD'")
            except Exception as e:
                print(f"   (Columns likely exist): {e}")

            # 2. Calculate holdings from journal_transactions
            print("2. Calculating positions from journal_transactions...")
            sql_calc = """
                SELECT ticker, 
                       SUM(CASE WHEN trade_type='BUY' THEN qty ELSE -qty END) as total_qty,
                       SUM(CASE WHEN trade_type='BUY' THEN qty * price ELSE -qty * price END) as total_amt
                FROM journal_transactions
                GROUP BY ticker
            """
            cur.execute(sql_calc)
            rows = cur.fetchall()

            # 3. Update managed_stocks
            print(f"3. Updating {len(rows)} stocks in managed_stocks...")
            for row in rows:
                ticker = row['ticker']
                qty = row['total_qty']
                amt = row['total_amt']
                
                if qty > 0:
                    avg_price = amt / qty
                else:
                    avg_price = 0
                    qty = 0 # No negative holdings allowed
                
                print(f"   -> {ticker}: Qty={qty}, Avg=${avg_price:.2f}")
                cur.execute("""
                    UPDATE managed_stocks 
                    SET quantity=%s, avg_price=%s
                    WHERE ticker=%s
                """, (qty, avg_price, ticker))

            # 4. Drop journal_transactions
            print("4. Dropping journal_transactions table...")
            cur.execute("DROP TABLE journal_transactions")
            
            conn.commit()
            print("✅ Migration Complete!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
