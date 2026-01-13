
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import manual_update_signal, get_v2_sell_status

def test_manual_target():
    ticker = "SOXS"
    price = 15.55
    key = "sell1"
    status = "SET_TARGET"

    print(f"Testing manual_update_signal({ticker}, {key}, {price}, {status})...")
    result = manual_update_signal(ticker, key, price, status)
    print(f"Result: {result}")

    if result:
        print("Verifying DB...")
        record = get_v2_sell_status(ticker)
        if record:
            target = record.get('manual_target_sell1')
            print(f"Target in DB: {target}")
            if float(target) == price:
                 print("✅ SUCCESS: Target saved correctly.")
            else:
                 print(f"❌ FAILURE: Target mismatch ({target} != {price})")
        else:
             print("❌ FAILURE: Record not found.")
    else:
        print("❌ FAILURE: Function returned False.")

if __name__ == "__main__":
    test_manual_target()
