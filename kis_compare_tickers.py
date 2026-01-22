import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.append(os.path.dirname(__file__))

from backend.kis_api_v2 import kis_client

def compare_tickers():
    tickers = ['SOXL', 'UPRO']
    print(f"🔍 Comparing {tickers} KIS Data...")
    
    for t in tickers:
        res = kis_client.get_price(t)
        if res:
            price = res.get('price')
            rate = res.get('rate')
            # diff = res.get('diff')
            base_calc = price / (1 + rate/100)
            
            print(f"\n[{t}]")
            print(f"  Price: {price}")
            print(f"  Rate: {rate}%")
            print(f"  Implied Base: {base_calc:.2f}")
            
            # Daily
            daily = kis_client.get_daily_price(t)
            if daily and len(daily) > 0:
                print(f"  Daily[0] (Today/Yest?): {daily[0]['xymd']} Close: {daily[0]['clos']}")
                print(f"  Daily[1] (Prev):        {daily[1]['xymd']} Close: {daily[1]['clos']}")
                
                # Check if Base matches Daily[1]
                if abs(base_calc - float(daily[1]['clos'])) < 0.05:
                     print(f"  => Base matches Prev Close (Result: DAILY CHANGE)")
                elif abs(base_calc - float(daily[0]['clos'])) < 0.05:
                     print(f"  => Base matches Daily[0] (Result: UNKNOWN)")
                else:
                     print(f"  => Base matches NEITHER (Result: DAYTIME OPEN?)")
        else:
            print(f"[{t}] Failed to fetch")

if __name__ == "__main__":
    compare_tickers()
