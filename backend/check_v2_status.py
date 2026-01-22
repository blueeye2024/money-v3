import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from db import get_v2_buy_status
    status = get_v2_buy_status('SOXL')
    print("======== SOXL V2 BUY STATUS ========")
    if status:
        print(f"Step 1 (Trend): {status.get('buy_sig1_yn')}  (Score +20)")
        print(f"Step 2 (Box/Sup): {status.get('buy_sig2_yn')}  (Score +20)")
        print(f"Step 3 (Entry): {status.get('buy_sig3_yn')}  (Score +30)")
        
        score = 0
        if status.get('buy_sig1_yn') == 'Y': score += 20
        if status.get('buy_sig2_yn') == 'Y': score += 20
        if status.get('buy_sig3_yn') == 'Y': score += 30
        print(f"------------------------------------")
        print(f"Total Base Score: {score}")
    else:
        print("No V2 Status Found for SOXL")
    print("====================================")

except Exception as e:
    print(f"Error: {e}")
