
import yfinance as yf
import pandas as pd
import pytz

def analyze_crossovers(ticker_symbol):
    print(f"Fetching data for {ticker_symbol}...")
    # 1. 데이터 가져오기 (최근 1개월, 5분 봉, 프리/애프터 마켓 포함)
    data_5m = yf.download(ticker_symbol, period="1mo", interval="5m", prepost=True, progress=False)
    
    if data_5m.empty:
        return f"{ticker_symbol}: 데이터를 가져오지 못했습니다."

    # Handle MultiIndex columns if present (Price, Ticker) -> just Price
    if isinstance(data_5m.columns, pd.MultiIndex):
        try:
            # If (Price, Ticker), we might just want to drop the level or select the ticker if present
            # But usually yf.download(single_ticker) might still have multiindex in new versions
            # Let's try to flatten or select
            if ticker_symbol in data_5m.columns.get_level_values(1):
                data_5m = data_5m.xs(ticker_symbol, axis=1, level=1)
        except:
            pass

    # Ensure clean columns
    # If it's still weird, just ensure we have 'Close'
    
    # 2. 30분 봉 데이터 생성 (리샘플링)
    # Resample logic: 5m data -> 30m bars.
    data_30m = data_5m.resample('30min').agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
    }).dropna()

    # 3. 이동평균선 계산 (10, 30)
    # 30분 봉
    data_30m['SMA10'] = data_30m['Close'].rolling(window=10).mean()
    data_30m['SMA30'] = data_30m['Close'].rolling(window=30).mean()
    
    # 5분 봉
    data_5m['SMA10'] = data_5m['Close'].rolling(window=10).mean()
    data_5m['SMA30'] = data_5m['Close'].rolling(window=30).mean()

    # 4. 30분 봉 골든크로스 탐지
    data_30m['prev_SMA10'] = data_30m['SMA10'].shift(1)
    data_30m['prev_SMA30'] = data_30m['SMA30'].shift(1)
    
    # Gold Cross: prev(SMA10 <= SMA30) and curr(SMA10 > SMA30)
    cross_30m = data_30m[
        (data_30m['prev_SMA10'] <= data_30m['prev_SMA30']) & 
        (data_30m['SMA10'] > data_30m['SMA30'])
    ]

    results = []

    # 5. 30분 골든크로스 발생 구간 내에서 5분 골든크로스 찾기
    tz_kr = pytz.timezone('Asia/Seoul')
    tz_ny = pytz.timezone('America/New_York')

    for timestamp in cross_30m.index:
        start_time = timestamp
        end_time = timestamp + pd.Timedelta(minutes=30)
        
        # 30분 Cross Time Formatted
        t_kr_30 = timestamp.replace(tzinfo=pytz.utc).astimezone(tz_kr).strftime('%Y-%m-%d %H:%M')
        t_ny_30 = timestamp.replace(tzinfo=pytz.utc).astimezone(tz_ny).strftime('%Y-%m-%d %H:%M')
        price_30 = data_30m.loc[timestamp]['Close']

        # 해당 30분 범위 내의 5분 데이터 추출
        window_5m = data_5m.loc[start_time:end_time].copy()
        
        # 5분 봉 골든크로스 확인 로직
        window_5m['prev_SMA10'] = window_5m['SMA10'].shift(1)
        window_5m['prev_SMA30'] = window_5m['SMA30'].shift(1)
        
        inner_cross = window_5m[
            (window_5m['prev_SMA10'] <= window_5m['prev_SMA30']) & 
            (window_5m['SMA10'] > window_5m['SMA30'])
        ]
        
        if not inner_cross.empty:
            for idx, row in inner_cross.iterrows():
                t_kr_5 = idx.replace(tzinfo=pytz.utc).astimezone(tz_kr).strftime('%Y-%m-%d %H:%M')
                t_ny_5 = idx.replace(tzinfo=pytz.utc).astimezone(tz_ny).strftime('%Y-%m-%d %H:%M')
                
                results.append({
                    'Ticker': ticker_symbol,
                    '30m_Cross_Time_KR': t_kr_30,
                    '30m_Cross_Time_NY': t_ny_30,
                    '30m_Price': f"{price_30:.2f}",
                    '5m_Signal_Time_KR': t_kr_5,
                    '5m_Signal_Time_NY': t_ny_5,
                    '5m_Price': f"{row['Close']:.2f}"
                })
        else:
            # 5분봉 크로스가 없더라도 30분봉 크로스 자체는 기록 (User might want to see it)
            # But user request says "when... data... 5m... crosses..."
            # Let's verify the user intent. "30분 ... 돌파했을 때 ... 5분 캔들이 돌파"
            # It implies both.
            # However, for debugging why "missing", let's include purely 30m ones too with note.
             results.append({
                'Ticker': ticker_symbol,
                '30m_Cross_Time_KR': t_kr_30,
                '30m_Cross_Time_NY': t_ny_30,
                '30m_Price': f"{price_30:.2f}",
                '5m_Signal_Time_KR': "N/A (Within 30m)",
                '5m_Signal_Time_NY': "-",
                '5m_Price': "-"
            })

    return pd.DataFrame(results)

# 실행
print("Running Analysis...")
df_soxl = analyze_crossovers("SOXL")
print("\n[SOXL RESULTS]")
if isinstance(df_soxl, pd.DataFrame) and not df_soxl.empty:
    print(df_soxl.to_string(index=False))
else:
    print("No events found.")

df_soxs = analyze_crossovers("SOXS")
print("\n[SOXS RESULTS]")
if isinstance(df_soxs, pd.DataFrame) and not df_soxs.empty:
    print(df_soxs.to_string(index=False))
else:
    print("No events found.")
