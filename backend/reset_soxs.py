
import db
conn = db.get_connection()
with conn.cursor() as cur:
    rows = cur.execute("UPDATE sell_stock SET sell_sig2_yn='N', manual_target_sell2=NULL WHERE ticker='SOXS'")
    conn.commit()
    print(f"Updated {rows} rows.")
print("Reset SOXS Signal 2")
