
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# Setup Timezones
tz_kr = pytz.timezone('Asia/Seoul')
tz_ny = pytz.timezone('America/New_York')

def calculate_sma(series, window):
    return series.rolling(window=window).mean()

def find_crosses(df, type_search='gold'):
    crosses = []
    if len(df) < 30: return crosses
    
    # Calculate SMAs
    df['SMA10'] = calculate_sma(df['Close'], 10)
    df['SMA30'] = calculate_sma(df['Close'], 30)
    
    dates = df.index
    sma10 = df['SMA10'].values
    sma30 = df['SMA30'].values
    close = df['Close'].values
    
    for i in range(1, len(df)):
        if pd.isna(sma10[i]) or pd.isna(sma30[i]): continue
        
        c_10 = sma10[i]
        c_30 = sma30[i]
        p_10 = sma10[i-1]
        p_30 = sma30[i-1]
        
        is_cross = False
        if type_search == 'gold':
            # Golden Cross: 10 crosses above 30
            if p_10 <= p_30 and c_10 > c_30: is_cross = True
        elif type_search == 'dead':
            # Dead Cross: 10 crosses below 30
            if p_10 >= p_30 and c_10 < c_30: is_cross = True
            
        if is_cross:
            # Timestamp processing
            ts = dates[i]
            if ts.tzinfo is None: ts = ts.replace(tzinfo=pytz.utc)
            
            ts_kr = ts.astimezone(tz_kr).strftime('%Y-%m-%d %H:%M')
            ts_ny = ts.astimezone(tz_ny).strftime('%Y-%m-%d %H:%M')
            
            try:
                p_val = float(close[i].item()) if hasattr(close[i], 'item') else float(close[i])
                sma10_val = float(c_10.item()) if hasattr(c_10, 'item') else float(c_10)
                sma30_val = float(c_30.item()) if hasattr(c_30, 'item') else float(c_30)
            except:
                p_val, sma10_val, sma30_val = 0.0, 0.0, 0.0

            crosses.append({
                'Time_KR': ts_kr,
                'Time_NY': ts_ny,
                'Price': f"{p_val:.2f}",
                'SMA10': f"{sma10_val:.2f}",
                'SMA30': f"{sma30_val:.2f}"
            })
    
    # Sort by time desc
    crosses.reverse()
    return crosses

def analyze_ticker(ticker):
    print(f"\n{'='*50}")
    print(f"Analyzing {ticker}")
    print(f"{'='*50}")
    
    # 1. Fetch Data (Enable Pre/Post Market)
    print(f"Fetching 30m data for {ticker} (Last 5 Days, Pre/Post Enabled)...")
    # Note: 1mo with 30m/5m might be too large or restricted by YF. 5d is safer for 5m/30m overlap check.
    try:
        df_30 = yf.download(ticker, period="5d", interval="30m", prepost=True, progress=False)
        print(f"Fetched {len(df_30)} rows for 30m.")
    except Exception as e:
        print(f"YF 30m Error: {e}")
        df_30 = pd.DataFrame()
    
    # 5m for Dead Cross
    print(f"Fetching 5m data for {ticker} (Last 5 Days, Pre/Post Enabled)...")
    try:
        df_5 = yf.download(ticker, period="5d", interval="5m", prepost=True, progress=False)
        print(f"Fetched {len(df_5)} rows for 5m.")
    except Exception as e:
        print(f"YF 5m Error: {e}")
        df_5 = pd.DataFrame()
    
    # Check Local DB
    print(f"\n[Checking Local DB for {ticker}]")
    try:
        from db import get_connection
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # 30m
                cursor.execute("SELECT count(*) FROM stock_price_history WHERE ticker=%s AND interval_type='30m'", (ticker,))
                cnt_30 = cursor.fetchone()[0]
                # 5m
                cursor.execute("SELECT count(*) FROM stock_price_history WHERE ticker=%s AND interval_type='5m'", (ticker,))
                cnt_5 = cursor.fetchone()[0]
                
                print(f"Local DB Rows -> 30m: {cnt_30}, 5m: {cnt_5}")
                
                # Get latest times
                cursor.execute("SELECT created_at FROM stock_price_history WHERE ticker=%s AND interval_type='30m' ORDER BY created_at DESC LIMIT 1", (ticker,))
                last_30 = cursor.fetchone()
                print(f"Last Local 30m: {last_30[0] if last_30 else 'None'}")
    except Exception as e:
        print(f"DB Check Error: {e}")

    # 2. Find 30m Golden Crosses
    golds_30 = find_crosses(df_30, 'gold')
    print(f"\n[Latest 30m Golden Crosses (SMA10 > SMA30)]")
    print(f"{'Time (KR)':<20} | {'Time (NY)':<20} | {'Price':<10}")
    print("-" * 60)
    for c in golds_30[:10]: # Show last 10
        print(f"{c['Time_KR']:<20} | {c['Time_NY']:<20} | ${c['Price']:<10}")
        
    # 3. Find 5m Dead Crosses
    deads_5 = find_crosses(df_5, 'dead')
    print(f"\n[Latest 5m Dead Crosses (SMA10 < SMA30)]")
    print(f"{'Time (KR)':<20} | {'Time (NY)':<20} | {'Price':<10}")
    print("-" * 60)
    for c in deads_5[:10]: # Show last 10
        print(f"{c['Time_KR']:<20} | {c['Time_NY']:<20} | ${c['Price']:<10}")

    # 4. Current Status
    curr_price = df_5['Close'].iloc[-1].item()
    curr_time = df_5.index[-1]
    if curr_time.tzinfo is None: curr_time = curr_time.replace(tzinfo=pytz.utc)
    curr_kr = curr_time.astimezone(tz_kr).strftime('%Y-%m-%d %H:%M')
    curr_ny = curr_time.astimezone(tz_ny).strftime('%Y-%m-%d %H:%M')
    
    print(f"\n[Current Status]")
    print(f"Time: {curr_kr} (KR) / {curr_ny} (NY)")
    print(f"Price: ${curr_price:.2f}")

if __name__ == "__main__":
    analyze_ticker("SOXL")
    analyze_ticker("SOXS")
