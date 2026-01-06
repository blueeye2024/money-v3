
from db import load_market_candles
from analysis import get_cross_history
import pandas as pd

print("DEBUG: Loading Candles from DB...")
df30 = load_market_candles("SOXL", "30m", limit=300)
df5 = load_market_candles("SOXL", "5m", limit=600)

print(f"Loaded 30m: {len(df30) if df30 is not None else 0}")
print(f"Loaded 5m: {len(df5) if df5 is not None else 0}")

if df30 is not None:
    print("Filtering Nulls 30m...")
    df30 = df30.dropna(subset=['Close'])
    print(f"After Filter 30m: {len(df30)}")

if df5 is not None:
    print("Filtering Nulls 5m...")
    df5 = df5.dropna(subset=['Close'])
    print(f"After Filter 5m: {len(df5)}")

print("Running get_cross_history...")
hist = get_cross_history(df30, df5)
print("History Output:", hist)
