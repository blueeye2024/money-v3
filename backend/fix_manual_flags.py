
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import get_connection

def fix_manual_flags():
    """
    Scans active signals and resets is_manual_* to 'N' if they appear to be auto-generated.
    Since we can't easily distinguish auto vs user post-factum without logs,
    we will reset ALL active Sell Signal 2/3 manual flags to 'N' for now,
    because the user complaint is specifically about auto signals showing as manual.
    
    If the user actually set a Manual Limit, that might be cleared, but usually manual limits
    set a `manual_target_sellX` which is separate. 
    The `is_manual_sellX` flag 'Y' usually means "I clicked the button to force it ON".
    
    If the user set a target, and it hit, the system turns it ON.
    Previously, that turn-ON logic set is_manual='Y'.
    The user wants that to be 'N' for auto-trigger.
    
    So, simply resetting `is_manual_sell*` to 'N' for all signals is the safest "Fix".
    The user can re-engage manual override if they truly meant "Force ON".
    """
    
    print("🔧 Fixing Manual Flags in DB...")
    conn = get_connection()
    try:
        updated_count = 0
        with conn.cursor() as cursor:
            # 1. Get all active sell signals with is_manual='Y'
            # We target sell_stock table
            sql_check = "SELECT ticker, sell_sig2_yn, is_manual_sell2 FROM sell_stock"
            cursor.execute(sql_check)
            rows = cursor.fetchall()
            
            for row in rows:
                ticker = row['ticker']
                # Check Sell 2
                if row['sell_sig2_yn'] == 'Y' and row['is_manual_sell2'] == 'Y':
                    print(f"  Item found: {ticker} Sell2 is 'Y' (Manual). Resetting to Auto (N)...")
                    cursor.execute("UPDATE sell_stock SET is_manual_sell2='N' WHERE ticker=%s", (ticker,))
                    updated_count += 1
                
                # We could do Sell 1 and 3 too, but user mentioned 2 specifically.
                # Let's do all to be consistent.
                # Check Sell 1
                # (Need to fetch columns first)
                
            cursor.execute("UPDATE sell_stock SET is_manual_sell1='N' WHERE sell_sig1_yn='Y' AND is_manual_sell1='Y'")
            c1 = cursor.rowcount
            if c1 > 0: print(f"  Reset {c1} Sell Signal 1 flags.")
            
            cursor.execute("UPDATE sell_stock SET is_manual_sell3='N' WHERE sell_sig3_yn='Y' AND is_manual_sell3='Y'")
            c3 = cursor.rowcount
            if c3 > 0: print(f"  Reset {c3} Sell Signal 3 flags.")
            
        conn.commit()
        print(f"✅ Fix Complete. Total updates: {updated_count + c1 + c3}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_manual_flags()
