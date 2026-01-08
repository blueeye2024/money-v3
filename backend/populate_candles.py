
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
    print(f"📡 {ticker} YFinance 다운로드 중...")
    df = yf.download(ticker, interval="5m", period="5d", prepost=True, progress=False)
    
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
    
    # 2. Logic to Merge KIS Data if stale
    # Check latest time in DF
    kis_candles = []
    
    # Calculate "Stale" threshold (e.g., 10 mins ago)
    now_ny = datetime.now(ny_tz)
    latest_yf_time = df.index[-1] if not df.empty else (now_ny - timedelta(days=1))
    
    # If latest YF data is older than 10 mins and it is currently market hours (or pre-market), try KIS
    # KIS API provides minute data.
    time_diff = (now_ny - latest_yf_time).total_seconds() / 60
    
    # Simple Logic: Always fetch KIS latest 5m candles and update/append to DF
    # Because YFinance might be delayed 15 mins.
    print(f"🔎 {ticker} YFinance 최신: {latest_yf_time.strftime('%H:%M')} (Diff: {int(time_diff)}m). KIS 실시간 조회 시도...")
    
    try:
        # Fetch KIS 5m candles
        # KIS returns list of dicts: {ktime: 'YYYYMMDDHHMMSS', last: 'price', vol: 'num'}
        # Note: KIS 'ktime' is usually KST. We must convert to NY.
        # Wait, overseas KIS might return Local time? 'ktime' for overseas usually YYYYMMDDHHMMSS in what zone?
        # Usually Local Time of the exchange (NY). Let's verify. 
        # Actually usually it is definitely purely local time string. 
        
        exchange_code = get_exchange_code(ticker)
        res_list = kis_client.get_minute_candles(ticker, 5, exchange_code) # 5m candles
        
        if res_list:
            print(f"📦 KIS 5분봉 {len(res_list)}개 수신 완료.")
            
            # KIS Data Processing
            kis_data = []
            for item in res_list:
                # item: {'dymd': '20250108', 'kymd': '20250109', 'xymd': '20250108', 'xhms': '093500', 'last': '98.50', ...}
                # Field names vary by API. overseas-price/v1/quotations/inquire-time-itemchartprice
                # Output fields: 'kymd'(Korea Date?), 'xhms'(Time?), 'last'(Close)
                
                # Careful: The output format in `kis_api.py` implementation relies on `output2`.
                # Typical KIS Overseas: 
                # kymd: Korean Date (e.g. 20260109)
                # kher: Korean Time (e.g. 093500) (?) No, wait.
                # Let's assume KIS API wrapper returns as-is.
                
                # Based on known KIS docs for overseas:
                # kymd: YYYYMMDD (KST date of request?)
                # kham: HHMMSS (KST time?) 
                # Actually, prefer using 'xymd' (Exchange Date) and 'xhms' (Exchange Time) if available.
                # If only kymd/ktime available, need conversion.
                
                # Let's inspect known keys if possible or try standard logic.
                # Standard fields: 'tymd' (local date), 'thms' (local time)?
                # Or 'kymd', 'khms'.
                
                date_str = item.get('tymd') or item.get('xymd') or item.get('kymd') # Date
                time_str = item.get('thms') or item.get('xhms') or item.get('khms') # Time
                price = float(item.get('last') or 0)
                vol = int(item.get('vols') or 0) # 'vols' is volume? or 'evol'?
                
                if not date_str or not time_str: continue
                
                # Construct datetime (NY Time assumed if using xymd/xhms)
                dt_str = f"{date_str}{time_str}"
                # If lengths are correct
                if len(dt_str) == 14: # YYYYMMDDHHMMSS
                    dt_obj = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
                else: 
                     continue
                     
                # Add TZ info (Assume NY Time for consistency with YF)
                dt_obj = ny_tz.localize(dt_obj)
                
                kis_data.append({
                    'timestamp': dt_obj,
                    'Close': price,
                    'Volume': vol
                })
            
            # Convert KIS List to DataFrame
            if kis_data:
                df_kis = pd.DataFrame(kis_data)
                df_kis.set_index('timestamp', inplace=True)
                
                # Merge: Update YF DF with KIS Data
                # Prioritize KIS data for overlapping times (since it's likely more realtime/official broker)
                # Combine: df.update(df_kis)? 
                if df.empty:
                    df = df_kis
                else:
                    # Combine indices
                    all_indices = df.index.union(df_kis.index)
                    df = df.reindex(all_indices)
                    df.update(df_kis) # Overwrite with KIS values where indices match
                    
                    # Also fill NaN if KIS has new rows
                    # df.update doesn't add new rows, only updates existing.
                    # So we used reindex above.
                    
                print(f"✅ KIS 데이터 병합 완료 (최종 {len(df)}개 캔들)")
        
    except Exception as e:
        print(f"⚠️ KIS Fallback Error: {e}")
        pass

    # --- Standard Processing (Same as before) ---
    
    unique_dates = sorted(list(set(df.index.date)))
    target_dates = unique_dates[-3:] # Keep last 3 days
    print(f"📅 {ticker} 최종 대상 날짜: {target_dates}")
    
    records = []
    seq = 1
    
    for timestamps in df.index:
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
