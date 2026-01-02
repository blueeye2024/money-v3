import yfinance as yf
import pandas as pd
from datetime import datetime, timezone

ticker = "SOXS"
data_30m = yf.download(ticker, period="2d", interval="30m", progress=False)

if not data_30m.empty:
    latest = data_30m.index[-1]
    print(f"Latest candle: {latest}")
    print(f"Latest candle UTC: {latest.tz_convert('UTC') if latest.tzinfo else latest}")
    print(f"Now UTC: {datetime.now(timezone.utc)}")
    
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    else:
        latest = latest.astimezone(timezone.utc)
    
    delta = datetime.now(timezone.utc) - latest
    print(f"Time since last candle: {delta.total_seconds()/3600:.1f} hours")
    print(f"Is stale (>12hr): {delta.total_seconds() > 43200}")
else:
    print("No data!")
