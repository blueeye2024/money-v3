import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis import run_analysis, _LATEST_REPORT
from db import fetch_signal_status_dict

print("--- 1. RUNNING DASHBOARD ANALYSIS (Refactored) ---")
# This should now just READ from DB, not calculate.
report = run_analysis()

soxs_report = None
if report and "stocks" in report:
    for s in report["stocks"]:
        if s["ticker"] == "SOXS":
            soxs_report = s
            break

print("\n--- DASHBOARD OUTPUT (SOXS) ---")
if soxs_report:
    print(f"Current Price: {soxs_report.get('current_price')}")
    print(f"Step 1: {soxs_report.get('step1')} ({soxs_report.get('step1_status')})")
    print(f"Step 2: {soxs_report.get('step2')} ({soxs_report.get('step2_status')})")
    print(f"Step 3: {soxs_report.get('step3')} ({soxs_report.get('step3_status')})")
    print(f"Final: {soxs_report.get('final')}")
else:
    print("SOXS not found in report!")

print("\n--- 2. DB TRUTH ---")
db_status = fetch_signal_status_dict('SOXS')
if db_status is None: db_status = {}
buy = db_status.get('buy', {})
if buy is None: buy = {}

print(f"Buy Sig 1: {buy.get('buy_sig1_yn')}")
print(f"Buy Sig 2: {buy.get('buy_sig2_yn')}")
print(f"Buy Sig 3: {buy.get('buy_sig3_yn')}")
print(f"Real Buy : {buy.get('real_buy_yn')}")

print("\n--- VERIFICATION ---")
match = True
if soxs_report:
    if bool(soxs_report.get('step1')) != (buy.get('buy_sig1_yn') == 'Y'): match = False
    if bool(soxs_report.get('step2')) != (buy.get('buy_sig2_yn') == 'Y'): match = False
    if bool(soxs_report.get('step3')) != (buy.get('buy_sig3_yn') == 'Y'): match = False
else:
    match = False

if match:
    print("✅ SUCCESS: Dashboard matches DB Truth.")
else:
    print("❌ FAILURE: Mismatch detected.")
