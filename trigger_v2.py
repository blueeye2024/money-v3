
import sys
import os

# Add backend to path
sys.path.append('/home/blue/blue/my_project/money/backend')
from analysis import run_v2_signal_analysis

if __name__ == "__main__":
    print("Triggering V2 Signal Analysis...")
    run_v2_signal_analysis()

    from db import get_v2_buy_status
    status = get_v2_buy_status('SOXS')
    print("\n--- Current SOXS Status ---")
    print(status)
    print("Done.")
