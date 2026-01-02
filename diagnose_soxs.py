import yfinance as yf
import pandas as pd
import datetime

def diagnose_soxs():
    ticker = "SOXS"
    print(f"--- Diagnosing {ticker} ({datetime.datetime.now()}) ---")
    
    # Use 1mo to ensure 30 SMA is fully populated
    data_30m = yf.download(ticker, period="1mo", interval="30m", progress=False)
    data_5m = yf.download(ticker, period="5d", interval="5m", progress=False)
    
    if data_30m.empty:
        print("30m Data Empty!")
        return
    if data_5m.empty:
        print("5m Data Empty!")
        return

    # 30m Check
    df30 = data_30m.copy()
    df30['SMA10'] = df30['Close'].rolling(window=10).mean()
    df30['SMA30'] = df30['Close'].rolling(window=30).mean()
    
    last_idx_30 = df30.index[-1]
    last_close_30 = df30['Close'].iloc[-1]
    last_sma10_30 = df30['SMA10'].iloc[-1]
    last_sma30_30 = df30['SMA30'].iloc[-1]
    f1 = last_sma10_30 > last_sma30_30
    
    print(f"[30m @ {last_idx_30}]")
    print(f"  Close: {last_close_30:.4f}")
    print(f"  SMA10: {last_sma10_30:.4f}")
    print(f"  SMA30: {last_sma30_30:.4f}")
    print(f"  Filter 1 (Trend UP): {f1}")

    # 5m Check
    df5 = data_5m.copy()
    df5['SMA10'] = df5['Close'].rolling(window=10).mean()
    df5['SMA30'] = df5['Close'].rolling(window=30).mean()
    
    last_idx_5 = df5.index[-1]
    last_sma10_5 = df5['SMA10'].iloc[-1]
    last_sma30_5 = df5['SMA30'].iloc[-1]
    f3 = last_sma10_5 > last_sma30_5
    
    print(f"[5m @ {last_idx_5}]")
    print(f"  SMA10: {last_sma10_5:.4f}")
    print(f"  SMA30: {last_sma30_5:.4f}")
    print(f"  Filter 3 (Timing UP): {f3}")

if __name__ == "__main__":
    diagnose_soxs()
