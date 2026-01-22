import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from analysis import run_analysis
    print("Running full analysis to capture SOXL state...")
    # force_update=True ensures fresh calculation
    report = run_analysis(force_update=True)
    
    soxl_res = next((x for x in report.get('stocks', []) if x['ticker'] == 'SOXL'), None)
    
    if soxl_res:
        print("--------------------------------------------------")
        print(f"Ticker: {soxl_res.get('ticker')}")
        print(f"Score: {soxl_res.get('score')}")
        print(f"Position: {soxl_res.get('position')}")
        print(f"Interpretation: {soxl_res.get('score_interpretation')}")
        print("--------------------------------------------------")
        
        # Check Price Alert Status explicitly
        from db import get_price_levels
        levels = get_price_levels('SOXL')
        print("Active Alerts in DB:")
        for lvl in levels:
            if lvl['is_active'] == 'Y':
                print(f" - {lvl['level_type']} #{lvl['stage']} ($ {lvl['price']}) : Triggered={lvl.get('triggered')}")
    else:
        print("SOXL not found in report.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
