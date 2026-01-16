
import sys
import os
import time

# Add backend directory to sys.path
sys.path.append('/home/blue/blue/my_project/money/backend')

from kis_api_v2 import kis_client

def test_kis():
    print("Testing KIS API for SOXL...")
    
    try:
        # Force token refresh if needed (internal logic handles it usually)
        # But let's just call get_price
        start = time.time()
        res = kis_client.get_price("SOXL", exchange="NYS")
        end = time.time()
        
        print("\n=== Result ===")
        print(f"Time: {end - start:.2f}s")
        print(f"Data: {res}")
        
        if res and res.get('price'):
            print(f"Success! Price: {res['price']}")
        else:
            print("Failed to get price.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_kis()
