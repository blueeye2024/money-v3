import yfinance as yf
import pandas as pd
from kis_api import kis_client
from datetime import datetime
import pytz

def test_gap_fill():
    ticker = "SOXL"
    print(f"--- [Test] Gap Filling check for {ticker} ---")
    
    # 1. Fetch YFinance (Delayed)
    print("1. Fetching YFinance 5m data... (SKIPPED due to Rate Limit)")
    # yf_ticker = yf.Ticker(ticker)
    # # interval 5m, period 1d
    # df_yf = yf_ticker.history(period="1d", interval="5m")
    # if not df_yf.empty:
    #     print(f"   Last YF Candle Time: {df_yf.index[-1]}")
    #     print(df_yf.tail(3)[['Close']])
    # else:
    #     print("   YF Data Empty")

    # 2. Fetch KIS Data (Realtime/Gap)
    print("\n2. Fetching KIS API 30m Minute Candles...")
    # interval 30 meant 30 minutes in KIS logic? or 30m?
    # kis_api.get_minute_candles doc says interval_min: 1, 3, 5... default 30
    # We want 5 minute candles to match 5m chart.
    kis_candles = kis_client.get_minute_candles(ticker, interval_min=5)
    
    if kis_candles:
        print(f"   KIS returned {len(kis_candles)} candles")
        # Print first few to see structure
        for i, c in enumerate(kis_candles[:5]):
            print(f"   [{i}] {c}")
    else:
        print("   KIS Data Empty or Failed")

if __name__ == "__main__":
    test_gap_fill()
