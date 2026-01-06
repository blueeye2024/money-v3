
import pandas as pd
import pandas_ta as ta

def check_antigravity_entry(df_5m, df_30m):
    """
    청안(Antigravity) 전략: 다중 시간프레임 골든크로스 탐색
    - 5분봉: 선행 신호 (단기 수급 확인)
    - 30분봉: 확정 신호 (중기 추세 확인)
    """
    
    # Ensure datetime index
    if not isinstance(df_5m.index, pd.DatetimeIndex):
        df_5m.index = pd.to_datetime(df_5m.index)
    if not isinstance(df_30m.index, pd.DatetimeIndex):
        df_30m.index = pd.to_datetime(df_30m.index)

    # 1. 이동평균선 계산 (SMA 5, 20)
    # Using 'Close' (standard varies, user code used 'close', adapting to our DB 'Close')
    close_col_5 = 'Close' if 'Close' in df_5m.columns else 'close'
    close_col_30 = 'Close' if 'Close' in df_30m.columns else 'close'
    
    df_5m['ma5'] = ta.sma(df_5m[close_col_5], length=5)
    df_5m['ma20'] = ta.sma(df_5m[close_col_5], length=20)
    
    df_30m['ma5'] = ta.sma(df_30m[close_col_30], length=5)
    df_30m['ma20'] = ta.sma(df_30m[close_col_30], length=20)

    # 2. 골든크로스 판별 함수 (현재 봉에서 크로스 발생 여부)
    def is_golden_cross(df):
        # 이전 봉에서는 ma5 < ma20 이고, 현재 봉에서는 ma5 > ma20 인 경우
        return (df['ma5'].shift(1) < df['ma20'].shift(1)) & (df['ma5'] > df['ma20'])

    df_5m['gc'] = is_golden_cross(df_5m)
    df_30m['gc'] = is_golden_cross(df_30m)
    
    # Debug
    # print("30m GC Count:", df_30m['gc'].sum())

    # 3. 전략 로직: 30분봉에서 GC가 발생한 시점에, 
    # 해당 시간 이전에 5분봉에서 이미 GC가 발생했었는지 확인
    # Get all 30m GC times
    gc_30m_indices = df_30m[df_30m['gc'] == True].index
    
    if len(gc_30m_indices) > 0:
        latest_30m_gc_time = gc_30m_indices[-1] # Target time (e.g., 06:00)
        
        # 30분봉 GC 발생 시간 기준, 최근 2시간 내에 5분봉 GC가 있었는지 탐색
        # Using slice instead of tail(24) for robust time lookup
        start_search = latest_30m_gc_time - pd.Timedelta(hours=2)
        lookback_5m = df_5m[(df_5m.index >= start_search) & (df_5m.index <= latest_30m_gc_time)]
        
        has_early_5m_gc = lookback_5m['gc'].any()
        
        if has_early_5m_gc:
            # Find the *first* or *last* 5m GC in that window? User code implies 'any', usually First is the "Lead Signal"
            # But user said "early_5m_time = ...iloc[-1]" which means the LATEST GC inside that window.
            early_5m_time = lookback_5m[lookback_5m['gc'] == True].index[-1]
            return {
                "status": "ENTRY_SIGNAL",
                "30m_gc_time": latest_30m_gc_time,
                "5m_gc_time": early_5m_time,
                "msg": f"🎯 진입점 포착! (5분봉: {early_5m_time.strftime('%H:%M')} / 30분봉: {latest_30m_gc_time.strftime('%H:%M')})"
            }

    return {"status": "WAIT", "msg": "조건을 충족하는 신호가 없습니다."}
