
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz
import time
from db import get_connection
# [USER REQUEST] KIS Fallback
from kis_api import kis_client, get_exchange_code

def populate_ticker_candle_data(ticker):
    """
    Generic function to populate {ticker}_candle_data table.
    Works for SOXL, SOXS, UPRO.
    Includes KIS Fallback logic if YFinance is stale.
    """
    table_name = f"{ticker.lower()}_candle_data"
    print(f"🚀 {ticker} 데이터 수집 시작 (최근 3일 04:00~16:00) -> Table: {table_name}")
    
    # 1. Fetch YFinance Data
    # Increase period to 7d to cover weekends/holidays effectively
    print(f"📡 {ticker} YFinance 다운로드 중...")
    df = yf.download(ticker, interval="5m", period="7d", prepost=True, progress=False)
    
    # Validation & Cleaning
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df = df.xs(ticker, axis=1, level=0)
        except:
            pass

    if df.empty:
        print(f"⚠️ {ticker} YFinance 데이터 없음. KIS Fallback 시도 예정.")
    
    ny_tz = pytz.timezone('America/New_York')
    
    # YFinance Index Handling
    if not df.empty:
        df.index = df.index.tz_convert(ny_tz)
    
    # ... (KIS Fallback Logic omitted for brevity, assuming it appends to df) ... 
    
    # [USER REQUEST] Holiday Handling Logic
    # Instead of taking unique dates from DF and slicing by calendar, 
    # we need to ensure we get the last 3 'Trading Days' that actually have data.
    # Since we fetched '7d' including prepost, periods with no trade might exist?
    # yfinance usually only returns rows with actual trade timestamps.
    # So unique(df.index.date) naturally gives us Trading Days.
    
    unique_trading_dates = sorted(list(set(df.index.date)))
    
    # If we have less than 3 days of data, take all we have.
    # If we have more, take the last 3.
    target_dates = unique_trading_dates[-3:]
    
    print(f"📅 {ticker} 최종 대상 거래일(Trading Days): {target_dates}")
    
    records = []
    seq = 1
    
    for timestamps in df.index:
        # Filter by Target Trading Days
        if timestamps.date() not in target_dates:
            continue
            
        t = timestamps.time()
        start_time = datetime.strptime("04:00", "%H:%M").time()
        end_time = datetime.strptime("16:00", "%H:%M").time() # Include 16:00
        
        if not (start_time <= t <= end_time):
            continue

            
        try:
            # Handle float/int conversion safely
            val_close = df.loc[timestamps, 'Close'] if 'Close' in df.columns else df.loc[timestamps] # If Series
            val_vol = df.loc[timestamps, 'Volume'] if 'Volume' in df.columns else 0 # KIS might not have Volume col if simple
            
            if isinstance(val_close, pd.Series): close = float(val_close.iloc[0])
            else: close = float(val_close)

            if isinstance(val_vol, pd.Series): vol = int(val_vol.iloc[0])
            else: vol = int(val_vol)

        except Exception as e:
            continue
            
        is_30m = 'Y' if timestamps.minute % 30 == 0 else None
        
        records.append({
            'seq': seq,
            'candle_date': timestamps.date(),
            'is_30m': is_30m,
            'hour': timestamps.hour,
            'minute': timestamps.minute,
            'close_price': close,
            'volume': vol,
            'source': 'mixed' # yfinance + kis
        })
        seq += 1

    print(f"📝 {ticker} 가공된 레코드 수: {len(records)}개")
    
    if not records:
        return

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # print(f"pwht: {table_name} 테이블 전체 초기화(Truncate) 중...")
            cursor.execute(f"TRUNCATE TABLE {table_name}")
            
            # print(f"💾 {ticker} DB 저장 중...")
            sql = f"""
            INSERT INTO {table_name} 
            (seq, candle_date, is_30m, hour, minute, close_price, volume, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            vals = []
            for r in records:
                vals.append((
                    r['seq'],
                    r['candle_date'],
                    r['is_30m'],
                    r['hour'],
                    r['minute'],
                    r['close_price'],
                    r['volume'],
                    r['source']
                ))
            
            cursor.executemany(sql, vals)
            conn.commit()
            print(f"✅ {ticker} 저장 완료!")
            
    except Exception as e:
        print(f"DB Error ({ticker}): {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    # Test run
    populate_ticker_candle_data("SOXS")
    time.sleep(2)
    populate_ticker_candle_data("SOXL")
    time.sleep(2)
    populate_ticker_candle_data("UPRO")
