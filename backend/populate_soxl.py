
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz
from db import get_connection

def populate_soxl_data():
    print("🚀 SOXL 데이터 수집 시작 (최근 3일, 04:00 ~ 16:00 NY Time)...")
    
    # 1. Fetch Data (5 days to be safe for T-2)
    print("📡 YFinance 다운로드 중...")
    df = yf.download("SOXL", interval="5m", period="5d", prepost=True, progress=False)
    
    if df.empty:
        print("❌ 데이터 없음.")
        return

    # Handle MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df = df.xs('SOXL', axis=1, level=0)
        except:
            pass

    # 2. Prepare Timezones
    ny_tz = pytz.timezone('America/New_York')
    kst_tz = pytz.timezone('Asia/Seoul')
    
    # 3. Filter Dates & Convert to KST
    df.index = df.index.tz_convert(kst_tz) # Convert to KST
    unique_dates = sorted(list(set(df.index.date)))
    
    # Keep only last 3 days
    target_dates = unique_dates[-3:]
    print(f"📅 대상 날짜: {target_dates}")
    
    # 4. Filter Time (04:00 ~ 16:00) & Dates
    records = []
    seq = 1
    
    for timestamps in df.index:
        if timestamps.date() not in target_dates:
            continue
            
        # [Ver 6.5] No Time Filter (Allow KST overnight)
        try:
            row = df.loc[timestamps]
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
            print("🗑️ 테이블 전체 초기화(Truncate) 중...")
            cursor.execute("TRUNCATE TABLE soxl_candle_data")
            
            print("💾 DB 저장 중...")
            sql = """
            INSERT INTO soxl_candle_data 
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
            print("✅ SOXL 데이터 저장 완료!")
            
    except Exception as e:
        print(f"DB Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    populate_soxl_data()
