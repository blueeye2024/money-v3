
import sys
import os
from datetime import datetime
import pytz

# Add backend to path
sys.path.append('/home/blue/blue/my_project/money/backend')
# Add backend to path
sys.path.append('/home/blue/blue/my_project/money/backend')
from db import get_connection

def force_soxs_signals():
    print("Forcing SOXS V2 Signals to COMPLETE...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Get current active cycle
    cursor.execute("SELECT manage_id FROM buy_stock WHERE ticker='SOXS' ORDER BY idx DESC LIMIT 1")
    row = cursor.fetchone()
    
    if not row:
        print("No active SOXS cycle found.")
        return
        
    manage_id = row['manage_id']
    print(f"Updating Manage ID: {manage_id}")
    
    now = datetime.now()
    
    # 2. Update Signals
    sql = """
        UPDATE buy_stock
        SET buy_sig2_yn = 'Y',
            buy_sig2_dt = %s,
            buy_sig2_price = 2.44,
            buy_sig3_yn = 'Y',
            buy_sig3_dt = %s,
            buy_sig3_price = 2.44,
            final_buy_yn = 'Y',
            final_buy_dt = %s,
            final_buy_price = 2.44
        WHERE manage_id = %s
    """
    cursor.execute(sql, (now, now, now, manage_id))
    conn.commit()
    print("✅ Signals Updated to Y/Y/Y (Final Y).")
    
    # 3. Log History
    from db import log_history
    log_history(manage_id, 'SOXS', '관리자강제', '2차/3차/진입 강제 확정', 2.44)
    print("✅ History Logged.")

if __name__ == "__main__":
    force_soxs_signals()
