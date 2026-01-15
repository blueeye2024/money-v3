
import db
conn = db.get_connection()
with conn.cursor() as cur:
    # Check Market Indices (Price Source)
    cur.execute("SELECT * FROM market_indices WHERE ticker='SOXS'")
    indices = cur.fetchone()
    print(f"📉 Market Indices (SOXS): {indices}")

    # Check Sell Status (Signal Trigger)
    cur.execute("SELECT * FROM sell_stock WHERE ticker='SOXS'")
    sell = cur.fetchone()
    print(f"🚦 Sell Stock (SOXS): Sig2={sell['sell_sig2_yn']}, Target2={sell['manual_target_sell2']}")

    conn.close()
