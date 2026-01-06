
from db import load_market_candles
from analysis import get_cross_history
import pandas as pd
import sys

print("DEBUG: Loading Candles from DB...")
# Using the increased limits
df30 = load_market_candles("SOXL", "30m", limit=1000)
df5 = load_market_candles("SOXL", "5m", limit=2000)

print(f"Loaded 30m: {len(df30) if df30 is not None else 0}")
print(f"Loaded 5m: {len(df5) if df5 is not None else 0}")

if df30 is not None: df30 = df30.dropna(subset=['Close'])
if df5 is not None: df5 = df5.dropna(subset=['Close'])

print("Running get_cross_history...")
hist = get_cross_history(df30, df5)

print("\n--- History Output ---")
import json
print(json.dumps(hist, indent=2, ensure_ascii=False))

if not hist['gold_30m']:
    print("WARNING: No 30m Gold Cross found!")
else:
    print(f"SUCCESS: Found {len(hist['gold_30m'])} 30m Gold Crosses")

if not hist['gold_5m']:
    print("WARNING: No 5m Gold Cross found!")
else:
    print(f"SUCCESS: Found {len(hist['gold_5m'])} 5m Gold Crosses")
