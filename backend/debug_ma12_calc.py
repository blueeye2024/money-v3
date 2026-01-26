
import sys
import os
import pandas as pd
import numpy as np

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis import check_triple_filter

def test_ma12():
    print("Testing check_triple_filter MA12 logic...")
    
    # Create dummy 5m data
    data = {
        'Close': [100.0 + i for i in range(20)],
        'MA10': [100.0] * 20,
        'MA30': [90.0] * 20
    }
    df5 = pd.DataFrame(data)
    
    # Calc expected MA12
    expected_ma12 = df5['Close'].rolling(window=12).mean().iloc[-1]
    print(f"Expected MA12: {expected_ma12}")
    
    # Call function
    # Note: check_triple_filter expects (ticker, data_30m, data_5m, ...)
    # Dashboard mode uses DB, but we want to test the MA12 calc block which uses passed DF if available?
    # Wait, in Dashboard mode (sim=False), it uses `data_5m` passed in only for `high_candidates` and now `ma12`.
    
    try:
        res = check_triple_filter('SOXL', None, df5, override_price=120.0, simulation_mode=False)
        print("Result Keys:", res.keys())
        print(f"Result MA12: {res.get('ma12')}")
        
        if res.get('ma12') == expected_ma12:
            print("✅ MA12 Calculation Success")
        else:
            print(f"❌ MA12 Calculation Failed (Got {res.get('ma12')})")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_ma12()
