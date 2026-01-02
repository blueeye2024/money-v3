
import sys
# Add backend directory
sys.path.append('/home/blue/blue/my_project/money/backend')
from db import get_last_candle_time

def check_time():
    print("=== DB Latest Data Check ===")
    for ticker in ["SOXL", "SOXS", "UPRO"]:
        last_30 = get_last_candle_time(ticker, "30m")
        last_5 = get_last_candle_time(ticker, "5m")
        print(f"[{ticker}]")
        print(f"  - 30m Last: {last_30}")
        print(f"  - 5m  Last: {last_5}")

if __name__ == "__main__":
    check_time()
