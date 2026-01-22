import sys
import os
import json

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.append(os.path.dirname(__file__))

from backend.kis_api_v2 import kis_client

def debug_kis_upro():
    ticker = "UPRO"
    print(f"🔍 DEBUG KIS API for {ticker}...")
    
    # 1. Get Exchange
    # code = kis_client.get_exchange_code(ticker) # Not exposed directly
    # Just try get_price
    
    res = kis_client.get_price(ticker)
    
    if res:
        print(f"\n[KIS Response Data]")
        print(json.dumps(res, indent=2))
        
        price = res.get('price')
        diff = res.get('diff')
        rate = res.get('rate')
        
        # Calculate manually to check base
        # If rate = (price - base) / base * 100
        # Then base = price / (1 + rate/100)
        
        base_calc = price / (1 + rate/100)
        print(f"\n[Analysis]")
        print(f"  Current Price: {price}")
        print(f"  Rate: {rate}%")
        print(f"  Implied Base Price: {base_calc:.2f}")
        
        # Get Daily Price (Yesterday Close)
        print(f"\n[Fetching Daily History to find Real Prev Close...]")
        daily = kis_client.get_daily_price(ticker)
        if daily and len(daily) > 0:
            first = daily[0] # Most recent (Today or Yesterday?)
            second = daily[1] if len(daily) > 1 else None
            
            print(f"  Daily[0] Date: {first['xymd']} Close: {first['clos']}")
            if second:
                print(f"  Daily[1] Date: {second['xymd']} Close: {second['clos']}")
            
            # Compare Implied Base with Daily Close
            # If Implied Base ~= Daily[0].Close (if today recorded) or Daily[1].Close
            
    else:
        print("Failed to fetch KIS data")

if __name__ == "__main__":
    debug_kis_upro()
