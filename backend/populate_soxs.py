
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz
from db import get_connection

def populate_soxs_data():
    print("🚀 SOXS 데이터 수집 시작 (최근 3일, 04:00 ~ 16:00 NY Time)...")
    
    # 1. Fetch Data (5 days to be safe for T-2)
    # interval="5m" allows max 60 days, but we only need recent.
    # prepost=True is ESSENTIAL for 04:00 start.
    print("📡 YFinance 다운로드 중...")
    df = yf.download("SOXS", interval="5m", period="5d", prepost=True, progress=False)
    
    if df.empty:
        print("❌ 데이터 없음.")
        return

    # Handle MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df = df.xs('SOXS', axis=1, level=0)
        except:
            pass # Maybe not multi-index or simple structure

    # 2. Prepare Timezones
    ny_tz = pytz.timezone('America/New_York')
    
    # 3. Filter Dates
    # Get unique dates from the index (converted to NY date)
    df.index = df.index.tz_convert(ny_tz)
    unique_dates = sorted(list(set(df.index.date)))
    
    # Keep only last 3 days (Today, T-1, T-2)
    target_dates = unique_dates[-3:]
    print(f"📅 대상 날짜: {target_dates}")
    
    # 4. Filter Time (04:00 ~ 16:00) & Dates
    records = []
    
    # Seq counter (reset per day? or global? user said "id, seq". Let's make seq global increment for this batch)
    seq = 1
    
    for timestamps in df.index:
        # Check Date
        if timestamps.date() not in target_dates:
            continue
            
        # Check Time (04:00 <= t <= 16:00)
        # 16:00 is close. usually range is inclusive start, exclusive end? 
        # But market data usually includes 16:00 trigger (Closing bell auction).
        # Let's include 16:00.
        t = timestamps.time()
        start_time = datetime.strptime("04:00", "%H:%M").time()
        end_time = datetime.strptime("16:00", "%H:%M").time()
        
        if not (start_time <= t <= end_time):
            continue
            
        # Extract Data
        # YFinance row might be Series if flat, or we access columns
        try:
            # Handle if columns are weird.
            row = df.loc[timestamps]
            # Since index is unique timestamps, row is Series
            close = float(row['Close'])
            vol = int(row['Volume'])
        except Exception as e:
            print(f"Row Error {timestamps}: {e}")
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

    print(f"📝 가공된 레코드 수: {len(records)}개")
    
    if not records:
        return

    # 5. Insert into DB
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Clean up target dates first to avoid duplicates (Simple approach)
            # Or just truncate if this is a refresh script? 
            # User might want to keep accumulating? 
            # "데이터 채워 넣을 것" usually implies filling. 
            # To be safe, let's DELETE specific dates and re-insert.
            
            # [USER REQUEST] Full Reset Logic
            print("pwht: 테이블 전체 초기화(Truncate) 중...")
            cursor.execute("TRUNCATE TABLE soxs_candle_data")
            
            # Bulk Insert
            print("💾 DB 저장 중...")
            sql = """
            INSERT INTO soxs_candle_data 
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
            print("✅ 저장 완료!")
            
    except Exception as e:
        print(f"DB Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    populate_soxs_data()
