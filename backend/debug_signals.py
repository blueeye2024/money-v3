
import pandas as pd
import yfinance as yf
from analysis import check_triple_filter, fetch_data
import json

def debug_signal():
    print("Fetching data...")
    d30, d5, d1, m, r = fetch_data(["SOXL", "SOXS"])
    
    print("\n--- SOXS Analysis ---")
    res_soxs = check_triple_filter("SOXS", d30, d5)
    print(json.dumps(res_soxs, indent=2))
    
    df_soxs = d30["SOXS"]
    print(f"SOXS Last 5 rows Close:\n{df_soxs['Close'].tail()}")
    
    print("\n--- SOXL Analysis ---")
    res_soxl = check_triple_filter("SOXL", d30, d5)
    print(json.dumps(res_soxl, indent=2))

if __name__ == "__main__":
    debug_signal()
