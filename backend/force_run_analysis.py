import sys
import os
import asyncio
# Need to set python path or run from bg dir
sys.path.append(os.getcwd())

from analysis import run_analysis
from db import get_connection

if __name__ == "__main__":
    print("Forcing Analysis Run...")
    # run_analysis is async or sync? Outline said run_analysis(holdings=None, force_update=False)
    # It seems synchronous based on outline scan not showing 'async def'.
    # But let's check.
    try:
        run_analysis(force_update=True)
        print("Analysis Run Complete.")
    except Exception as e:
        print(f"Analysis Error: {e}")
        import traceback
        traceback.print_exc()

    # Check DB result
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT ticker, sell_sig2_yn FROM sell_stock WHERE ticker='SOXL'")
        print(f"DB State: {cur.fetchall()}")
    conn.close()
