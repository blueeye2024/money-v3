
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
from db import get_connection

def populate_ticker_candle_data(ticker):
    """
    Generic function to populate {ticker}_candle_data table.
    Works for SOXL, SOXS.
    """
    table_name = f"{ticker.lower()}_candle_data"
    print(f"🚀 {ticker} 데이터 수집 시작 (최근 3일, 04:00 ~ 16:00 NY Time) -> Table: {table_name}")
    
    # 1. Fetch Data
    print(f"📡 {ticker} YFinance 다운로드 중...")
    df = yf.download(ticker, interval="5m", period="5d", prepost=True, progress=False)
    
    if df.empty:
        print(f"❌ {ticker} 데이터 없음.")
        return

    if isinstance(df.columns, pd.MultiIndex):
        try:
            df = df.xs(ticker, axis=1, level=0)
        except:
            pass

    ny_tz = pytz.timezone('America/New_York')
    df.index = df.index.tz_convert(ny_tz)
    unique_dates = sorted(list(set(df.index.date)))
    target_dates = unique_dates[-3:]
    print(f"📅 {ticker} 대상 날짜: {target_dates}")
    
    records = []
    seq = 1
    
    for timestamps in df.index:
        if timestamps.date() not in target_dates:
            continue
            
        t = timestamps.time()
        start_time = datetime.strptime("04:00", "%H:%M").time()
        end_time = datetime.strptime("16:00", "%H:%M").time()
        
        if not (start_time <= t <= end_time):
            continue
            
        try:
            val_close = df.loc[timestamps, 'Close']
            val_vol = df.loc[timestamps, 'Volume']
            
            # Handle if it's a Series (single row) or scalar
            if isinstance(val_close, pd.Series):
                 close = float(val_close.iloc[0])
            else:
                 close = float(val_close)

            if isinstance(val_vol, pd.Series):
                 vol = int(val_vol.iloc[0])
            else:
                 vol = int(val_vol)

        except Exception as e:
            # print(f"Row Error {timestamps}: {e}")
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
            'source': 'yfinance'
        })
        seq += 1

    print(f"📝 {ticker} 가공된 레코드 수: {len(records)}개")
    
    if not records:
        return

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print(f"pwht: {table_name} 테이블 전체 초기화(Truncate) 중...")
            cursor.execute(f"TRUNCATE TABLE {table_name}")
            
            print(f"💾 {ticker} DB 저장 중...")
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
    populate_ticker_candle_data("SOXL")
