import sys
import os
import pandas as pd
# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis import determine_market_regime_v2

print("Running determine_market_regime_v2...")
try:
    from analysis import fetch_data
    print("Fetching Data...")
    daily, d30, d5 = fetch_data()
    
    # Run analysis
    result = determine_market_regime_v2(daily_data=daily, data_30m=d30, data_5m=d5)
    
    # Check results for SOXL
    # Structure: result -> market_regime -> details -> prime_guide
    mr = result.get('market_regime', {})
    details = mr.get('details', {})
    prime_guide = details.get('prime_guide', {})
    scores = prime_guide.get('scores', {})
    
    if 'SOXL' in scores:
        soxl_data = scores['SOXL']
        print("\n--- SOXL Metrics ---")
        print(f"Score: {soxl_data.get('score')}")
        print(f"New Metrics: {soxl_data.get('new_metrics')}")
    else:
        print("SOXL data not found in results.")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
