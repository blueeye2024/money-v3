import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))

try:
    from kis_api import kis_client
    print("Attempting to fetch SOXL price from KIS API (Smart Detection)...")
    
    # Test High Level get_price
    smart_res = kis_client.get_price('SOXL')
    print(f"\n[Smart get_price Result]: {smart_res}")
    
    if smart_res and smart_res['exchange'] in ['BAA', 'BAQ', 'BAY']:
         print("SUCCESS: Automatically selected Daytime Exchange!")
    elif smart_res and smart_res['tvol'] > 0:
         print(f"SUCCESS: selected Active Exchange {smart_res['exchange']} with Vol {smart_res['tvol']}")
    else:
         print("WARNING: Did not select Daytime exchange or no volume.")

    # Test SOXS as well since user provided live data for it
    tickers = ['SOXL', 'SOXS']
    
    for t in tickers:
        print(f"\n--- Testing {t} ---")
        # Direct call to see raw output
        # We need to access the internal method or copy code to see raw json
        # Let's verify what get_price_request returns
        
        # Manually loop exchanges to find where the data is
        for ex in ['NAS', 'NYS', 'AMS', 'BAQ', 'BAY', 'PAC', 'BAA']: # Added BAA
            print(f"Checking {ex}...")
            res = kis_client._fetch_price_request(ex, t)
            if res:
                print(f"[{ex}] Raw Response: {res}")
                if res.get('rt_cd') == '0':
                    out = res.get('output', {})
                    print(f"  => Price: {out.get('last')}, Diff: {out.get('diff')}, Rate: {out.get('rate')}")
            else:
                 print(f"[{ex}] No Response")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
