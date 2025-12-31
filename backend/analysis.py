
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import os
import time
import re

# Global Cache for Historical Data
_DATA_CACHE = {
    "30m": None,
    "5m": None,
    "market": None,
    "last_fetch": 0
}


def get_score_interpretation(score, position_text=""):
    is_sell = "매도" in position_text or "하단" in position_text
    if score >= 80: return "🚨긴급 매도" if is_sell else "✨강력 매수"
    if score >= 70: return "📉매도" if is_sell else "🟢매수"
    if score >= 50: return "⚠경계" if is_sell else "🟡관망"
    return "📉조정" if is_sell else "⚪관망"

# Stock Names Mapping
TICKER_NAMES = {
    "SOXL": "Direxion Daily Semiconductor Bull 3X",
    "SOXS": "Direxion Daily Semiconductor Bear 3X",
    "UPRO": "ProShares UltraPro S&P500 (3X)",
    "AAAU": "Goldman Sachs Physical Gold ETF",
    "TSLA": "Tesla Inc.",
    "IONQ": "IonQ Inc.",
    "AMZU": "Direxion Daily AMZN Bull 1.5X",
    "UFO": "Procure Space ETF",
    "GOOGL": "Alphabet Inc. Class A",
    "XPON": "Expion360 Inc."
}

# Tickers List (Collected from keys)
TARGET_TICKERS = list(TICKER_NAMES.keys())

MARKET_INDICATORS = {
    "S&P500": "^GSPC",
    "NASDAQ": "^IXIC",
    "GOLD": "GC=F",
    "KRW": "KRW=X"
}

def get_current_time_str():
    kst = pytz.timezone('Asia/Seoul')
    est = pytz.timezone('US/Eastern')
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    
    now_kst = now_utc.astimezone(kst)
    now_est = now_utc.astimezone(est)
    
    return {
        "kst": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
        "est": now_est.strftime("%m/%d %H:%M:%S"),
        "full_str": f"{now_kst.strftime('%Y-%m-%d %H:%M:%S')} KST (EST: {now_est.strftime('%m/%d %H:%M:%S')})"
    }

def get_current_time_str_sms():
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(timezone.utc).astimezone(kst)
    return now_kst.strftime("%Y.%m.%d %H:%M")

def fetch_data(tickers=None):
    global _DATA_CACHE
    
    target_list = tickers if tickers else TARGET_TICKERS
    
    # Check Cache (Only if default tickers used, for simplicity)
    if tickers is None and time.time() - _DATA_CACHE["last_fetch"] < 300 and _DATA_CACHE["30m"] is not None:
        # Return cached data
        return _DATA_CACHE["30m"], _DATA_CACHE["5m"], _DATA_CACHE.get("1d"), _DATA_CACHE["market"], _DATA_CACHE.get("regime")

    # Fetch 30m data (Main) for Stocks
    tickers_str = " ".join(target_list)
    
    print(f"Fetching 30m data for {len(target_list)} Stocks...")
    # Hide progress to keep logs clean
    data_30m = yf.download(tickers_str, period="5d", interval="30m", prepost=True, group_by='ticker', threads=False, progress=False)
    
    print(f"Fetching 5m data for {len(target_list)} Stocks...")
    data_5m = yf.download(tickers_str, period="5d", interval="5m", prepost=True, group_by='ticker', threads=False, progress=False)

    print(f"Fetching 1d data for {len(target_list)} Stocks...")
    data_1d = yf.download(tickers_str, period="1y", interval="1d", prepost=True, group_by='ticker', threads=False, progress=False)
    
    # Market indicators - Use Ticker.history for stability
    print("Fetching market data (Indices)...")
    market_data = {}
    for name, ticker in MARKET_INDICATORS.items():
        try:
            t = yf.Ticker(ticker)
            # Fetch history (need enough for prev close)
            hist = t.history(period="5d")
            if not hist.empty:
                market_data[name] = hist
            else:
                print(f"Warning: No data for {name}")
                market_data[name] = pd.DataFrame()
        except Exception as e:
            print(f"Failed to fetch {name}: {e}")
            market_data[name] = pd.DataFrame()
            
    # Fetch Daily data for Market Regime (UPRO, S&P500, NASDAQ)
    print("Fetching Daily data for Market Regime...")
    regime_tickers = ["UPRO", "^GSPC", "^IXIC"]
    regime_data = yf.download(regime_tickers, period="1y", interval="1d", group_by='ticker', threads=False, progress=False)

    print("Data fetch complete.")
    
    # Update Cache (Only if default)
    if tickers is None:
        _DATA_CACHE["30m"] = data_30m
        _DATA_CACHE["5m"] = data_5m
        _DATA_CACHE["1d"] = data_1d
        _DATA_CACHE["market"] = market_data
        _DATA_CACHE["regime"] = regime_data
        _DATA_CACHE["last_fetch"] = time.time()
    
    return data_30m, data_5m, data_1d, market_data, regime_data

def calculate_sma(series, window):
    return series.rolling(window=window).mean()

def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

    return 100 - (100 / (1 + rs))

def calculate_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def calculate_atr(df, window=14):
    high = df['High']
    low = df['Low']
    close = df['Close'].shift(1)
    
    tr1 = high - low
    tr2 = (high - close).abs()
    tr3 = (low - close).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=window).mean()

def calculate_adx(df, window=14):
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    # TR
    close_shift = close.shift(1)
    tr1 = high - low
    tr2 = (high - close_shift).abs()
    tr3 = (low - close_shift).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # DM
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    # Smooth (Wilder's Smoothing is complicated, using SMA for approx)
    tr_s = tr.rolling(window=window).mean()
    plus_dm_s = pd.Series(plus_dm, index=df.index).rolling(window=window).mean()
    minus_dm_s = pd.Series(minus_dm, index=df.index).rolling(window=window).mean()
    
    # DI
    plus_di = 100 * (plus_dm_s / tr_s)
    minus_di = 100 * (minus_dm_s / tr_s)
    
    # DX
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
    
    # ADX
    adx = dx.rolling(window=window).mean()
    return adx

def check_box_pattern(df_30m, days=7, tolerance=5.0):
    """
    Check box pattern with flexible tolerance.
    Default: 7 days, 5% range.
    Returns: (is_box, high_val, low_val, pct_diff)
    """
    if df_30m.empty:
        return False, 0, 0, 0

    last_idx = df_30m.index[-1]
    cutoff_time = last_idx - timedelta(days=days)
    
    recent_data = df_30m[df_30m.index >= cutoff_time]
    
    if recent_data.empty:
        return False, 0, 0, 0
        
    high_max = recent_data['High'].max()
    low_min = recent_data['Low'].min()
    
    if low_min == 0: return False, 0, 0, 0
    
    diff_pct = ((high_max - low_min) / low_min) * 100
    
    is_box = diff_pct <= tolerance
    return is_box, high_max, low_min, diff_pct

def parse_strategy_config(strategy_str):
    config = {
        "ma_type": "sma", 
        "ma_fast": 10,
        "ma_slow": 30,
        "box_tol": None,
        "vol_req": None,
        "rsi_min": None,
        "daily_ema200": False,
        "daily_sma200": False
    }
    if not strategy_str: return config
    
    # MA Check
    ma_match = re.search(r'(EMA|SMA)\s*(\d+)/(\d+)', strategy_str, re.IGNORECASE)
    if ma_match:
        config['ma_type'] = ma_match.group(1).lower()
        config['ma_fast'] = int(ma_match.group(2))
        config['ma_slow'] = int(ma_match.group(3))
        
    # Box check
    box_match = re.search(r'박스권\s*(\d+(\.\d+)?)%', strategy_str)
    if box_match:
        config['box_tol'] = float(box_match.group(1))
        
    # Volume
    vol_match = re.search(r'거래량\s*(\d+)%', strategy_str)
    if vol_match:
        config['vol_req'] = float(vol_match.group(1))
        
    # RSI
    rsi_match = re.search(r'RSI\s*(\d+)', strategy_str, re.IGNORECASE)
    if rsi_match:
        config['rsi_min'] = float(rsi_match.group(1))
        
    # Daily Filter
    if "일봉 EMA 200" in strategy_str or "EMA 200 필터" in strategy_str:
        config['daily_ema200'] = True
    if "일봉 SMA 200" in strategy_str or "SMA 200 위에서만" in strategy_str:
        config['daily_sma200'] = True
        
    return config

def analyze_ticker(ticker, df_30mRaw, df_5mRaw, df_1dRaw, market_vol_score=0, is_held=False, real_time_info=None, holdings_data=None, strategy_info=None):
    # Retrieve Stock Name
    stock_name = TICKER_NAMES.get(ticker, ticker)
    
    try:
        # Match ticker using MultiIndex or Flat
        df_30 = None
        df_5 = None
        df_1d = None

        if isinstance(df_30mRaw.columns, pd.MultiIndex):
            if ticker in df_30mRaw.columns.levels[0]:
                df_30 = df_30mRaw[ticker].copy()
                df_30.dropna(subset=['Close'], inplace=True)
        elif ticker in df_30mRaw.columns:
             pass 

        if isinstance(df_5mRaw.columns, pd.MultiIndex):
            if ticker in df_5mRaw.columns.levels[0]:
                df_5 = df_5mRaw[ticker].copy()
                df_5.dropna(subset=['Close'], inplace=True)
                
        if df_1dRaw is not None:
            if isinstance(df_1dRaw.columns, pd.MultiIndex):
                if ticker in df_1dRaw.columns.levels[0]:
                    df_1d = df_1dRaw[ticker].copy()
                    df_1d.dropna(subset=['Close'], inplace=True)
        
        if df_30 is None or df_5 is None or df_30.empty or df_5.empty:
            return {"ticker": ticker, "name": stock_name, "error": "No data"}
            
        # ... (Technical Analysis Logic remains mostly same, need to ensure return dict has 'name')
        
        # Calculate Indicators 30m
        df_30['SMA10'] = calculate_sma(df_30['Close'], 10)
        df_30['SMA30'] = calculate_sma(df_30['Close'], 30)
        df_30['RSI'] = calculate_rsi(df_30['Close'])
        
        # Bollinger Bands & MACD
        df_30['BB_Mid'] = df_30['Close'].rolling(window=20).mean()
        df_30['BB_Std'] = df_30['Close'].rolling(window=20).std()
        df_30['BB_Upper'] = df_30['BB_Mid'] + (2 * df_30['BB_Std'])
        df_30['BB_Lower'] = df_30['BB_Mid'] - (2 * df_30['BB_Std'])
        
        exp12 = df_30['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df_30['Close'].ewm(span=26, adjust=False).mean()
        df_30['MACD'] = exp12 - exp26
        df_30['Signal'] = df_30['MACD'].ewm(span=9, adjust=False).mean()

        # 5m
        df_5['SMA10'] = calculate_sma(df_5['Close'], 10)
        df_5['SMA30'] = calculate_sma(df_5['Close'], 30)
        
        # Values
        current_price = df_30['Close'].iloc[-1]
        prev_price = df_30['Close'].iloc[-2]
        change_pct = ((current_price - prev_price) / prev_price) * 100
        
        # Override with Real-time Info if available
        if real_time_info:
            current_price = float(real_time_info['price'])
            # rate is percentage change (e.g. +0.03 means 0.03%)
            change_pct = float(real_time_info['rate'])
            # Note: Indicator checks below (SMA, Cross) use df_30 (Candle Close). 
            # This is acceptable (Signals on close, Price on live).
            # But Box Breakout uses `current_price` variable, so it will be accurate.
        
        # Signal Detection (Previous Logic)
        last_sma10 = df_30['SMA10'].iloc[-1]
        last_sma30 = df_30['SMA30'].iloc[-1]
        last_5m_sma10 = df_5['SMA10'].iloc[-1]
        last_5m_sma30 = df_5['SMA30'].iloc[-1]
        is_box, box_high, box_low, box_pct = check_box_pattern(df_30)
        
        position = "관망"
        recent_cross_type = None 
        signal_time = ""
        cross_idx = -1
        
        for i in range(1, 50):
            if i >= len(df_30): break
            c_sma10 = df_30['SMA10'].iloc[-i]
            # ... (Rest of cross detection logic)
            c_sma30 = df_30['SMA30'].iloc[-i]
            p_sma10 = df_30['SMA10'].iloc[-(i+1)]
            p_sma30 = df_30['SMA30'].iloc[-(i+1)]
            
            if p_sma10 <= p_sma30 and c_sma10 > c_sma30:
                recent_cross_type = 'gold'
                cross_idx = -i
                signal_time = df_30.index[-i]
                break
            elif p_sma10 >= p_sma30 and c_sma10 < c_sma30:
                recent_cross_type = 'dead'
                cross_idx = -i
                signal_time = df_30.index[-i]
                break
        
        # Trend Following Fallback
        if recent_cross_type is None:
            if last_sma10 > last_sma30:
                 recent_cross_type = 'gold'
            else:
                 recent_cross_type = 'dead'
            signal_time = df_30.index[-1]

            if last_sma10 > last_sma30:
                 recent_cross_type = 'gold'
            else:
                 recent_cross_type = 'dead'
            signal_time = df_30.index[-1]

        # Calculate Extra Indicators for Strategy
        # Volume Ratio (5m)
        vol_ratio = 0.0
        if not df_5.empty and len(df_5) > 20:
            curr_vol = df_5['Volume'].iloc[-1]
            avg_vol = df_5['Volume'].iloc[-21:-1].mean()
            if avg_vol > 0:
                vol_ratio = (curr_vol / avg_vol) * 100
        
        # EMA for UPRO/TMF (15, 50, 200) on 30m? Or 30m?
        # Strategy says "EMA 15/50 Golden Cross" -> assume 30m
        df_30['EMA15'] = calculate_ema(df_30['Close'], 15)
        df_30['EMA50'] = calculate_ema(df_30['Close'], 50)
        
        last_ema15 = df_30['EMA15'].iloc[-1]
        last_ema50 = df_30['EMA50'].iloc[-1]
        
        # === Cheongan 2.1: Dynamic Strategy Overlay (DB Driven) ===
        strategy_desc = "Standard Formula"
        pass_filter = True
        
        if strategy_info:
             # Parse
             st_conf = parse_strategy_config(strategy_info.get('buy_strategy', ''))
             desc_log = []
             
             # 1. Custom MA Cross Check (if different from default SMA 10/30)
             if st_conf['ma_type'] != 'sma' or st_conf['ma_fast'] != 10 or st_conf['ma_slow'] != 30:
                 # Re-calculate Cross
                 c_ma_cross = None
                 c_idx = -1
                 c_sig_time = ""
                 
                 # Calc indicators on df_30
                 fast_col = f"MA_FAST_{st_conf['ma_fast']}"
                 slow_col = f"MA_SLOW_{st_conf['ma_slow']}"
                 
                 if st_conf['ma_type'] == 'ema':
                     df_30[fast_col] = calculate_ema(df_30['Close'], st_conf['ma_fast'])
                     df_30[slow_col] = calculate_ema(df_30['Close'], st_conf['ma_slow'])
                     desc_log.append(f"Strat:EMA{st_conf['ma_fast']}/{st_conf['ma_slow']}")
                 else:
                     df_30[fast_col] = calculate_sma(df_30['Close'], st_conf['ma_fast'])
                     df_30[slow_col] = calculate_sma(df_30['Close'], st_conf['ma_slow'])
                     desc_log.append(f"Strat:SMA{st_conf['ma_fast']}/{st_conf['ma_slow']}")
                     
                 # Scan for cross
                 for i in range(1, 50):
                     if i >= len(df_30): break
                     c_f = df_30[fast_col].iloc[-i]
                     c_s = df_30[slow_col].iloc[-i]
                     p_f = df_30[fast_col].iloc[-(i+1)]
                     p_s = df_30[slow_col].iloc[-(i+1)]
                     
                     if p_f <= p_s and c_f > c_s:
                         c_ma_cross = 'gold'
                         c_idx = -i
                         c_sig_time = df_30.index[-i]
                         break
                     elif p_f >= p_s and c_f < c_s:
                         c_ma_cross = 'dead'
                         c_idx = -i
                         c_sig_time = df_30.index[-i]
                         break
                 
                 # Override Global Result
                 recent_cross_type = c_ma_cross
                 cross_idx = c_idx
                 if c_sig_time: signal_time = c_sig_time
                 
             # 2. Box Filter
             if st_conf['box_tol']:
                 if recent_cross_type == 'gold':
                     c_is_box, c_box_high, _, _ = check_box_pattern(df_30, tolerance=st_conf['box_tol'])
                     if c_is_box:
                         if current_price > c_box_high:
                             desc_log.append(f"BoxBreak(>{st_conf['box_tol']}%):OK")
                         else:
                             pass_filter = False
                             desc_log.append(f"BoxBreak:Fail(Price<=High)")
                     else:
                         # Strategy usually implies we want to catch the breakout.
                         # If no box, we pass (lenient) or fail?
                         # Let's say lenient for now unless explicitly strict.
                         desc_log.append("NoBox:Pass")

             # 3. Volume Filter
             if st_conf['vol_req']:
                 if recent_cross_type == 'gold':
                      if vol_ratio < st_conf['vol_req']:
                          pass_filter = False
                          desc_log.append(f"Vol({vol_ratio:.0f}% < {st_conf['vol_req']}%)")

             # 4. RSI Filter (Min)
             if st_conf['rsi_min']:
                  if recent_cross_type == 'gold':
                      rsi_val = df_30['RSI'].iloc[-1]
                      if rsi_val < st_conf['rsi_min']:
                          pass_filter = False
                          desc_log.append(f"RSI({rsi_val:.1f} < {st_conf['rsi_min']})")
                          
             # 5. Daily MA Filter
             if st_conf['daily_ema200'] or st_conf['daily_sma200']:
                 if recent_cross_type == 'gold':
                     if df_1d is not None and len(df_1d) >= 200:
                          d_close = df_1d['Close'].iloc[-1]
                          ma_val = 0
                          if st_conf['daily_ema200']:
                              ma_val = calculate_ema(df_1d['Close'], 200).iloc[-1]
                              lbl = "EMA200"
                          else:
                              ma_val = calculate_sma(df_1d['Close'], 200).iloc[-1]
                              lbl = "SMA200"
                              
                          if d_close < ma_val:
                              pass_filter = False
                              desc_log.append(f"Daily{lbl}:Fail(Close<MA)")
                          else:
                              desc_log.append(f"Daily{lbl}:OK")
                     else:
                          desc_log.append("DailyMA:NoData") 

             if desc_log: strategy_desc = ", ".join(desc_log)
        
        # Force "Observing" if filter failed
        if not pass_filter and recent_cross_type == 'gold':
             # If filter failed, we ignore the Gold Cross
             recent_cross_type = None 
             # Logic fallthrough to 'Trend Following Fallback' or just 'Observe'
             # If we set recent_cross_type to None, it hits fallback.
             # Better to specificy "Weak" or "Filtered".
             pass
        
        # Force Signal Time to Current Real-time Update (User Request)
        # Since we use Real-time Price and re-evaluate Breakout/Position,
        # we update the signal timestamp to reflect the latest analysis time.
        kst = pytz.timezone('Asia/Seoul')
        signal_time = datetime.now(kst)

        # Validation
        valid = True
        if recent_cross_type == 'gold':
            if last_5m_sma10 < last_5m_sma30: valid = False
            if is_box:
                if current_price > box_high: pass
                else: valid = False
            position = "🚨 매수 진입" if cross_idx == -1 else "🔴 매수 유지" if valid else "관망 (매수 신호 무효화)"
        elif recent_cross_type == 'dead':
            if last_5m_sma10 > last_5m_sma30: valid = False
            if is_box:
                 if current_price < box_low: pass
                 else: valid = False
            position = "🚨 매도 진입" if cross_idx == -1 else "🔵 매도 유지" if valid else "관망 (매도 신호 무효화)"
            
            if current_price > box_high: position = "✨ 박스권 돌파 성공 (상단)"
            elif current_price < box_low: position = "✨ 박스권 돌파 성공 (하단)"
            
        # === User Holding Based Position Overlay ===
        # If Held: Buy/Hold/Observe -> "매수 유지", Sell -> "매도"
        # If Not Held: Buy -> "매수", Sell/Observe -> "미보유"
        
        algo_position = position # Save algo string for scoring?
        # Actually score depends on `is_buy_signal` derived from `position` text.
        # Refined Logic:
        # We need to construct a display string (`final_position`) AND ensure scoring logic uses the ALGO signal, not the display string?
        # User said "보유하고 있지 않은 종목은 ... 미보유라고 하면되". 
        # But for Scoring? "미보유" typically scores 0 (Base 20 if observes?).
        # If I change `position` string, downstream logic (`is_buy_signal`) changes.
        
        # Let's derive `is_buy_signal` etc. from `position` BEFORE overriding it for display?
        # But `analyze_ticker` returns `position` for display.
        # I should keep `position` as the final display string.
        # But calculate Scores based on technicals (Algo Position).
        # However, if I display "미보유", the Dashboard shouldn't show "Buy Score 80".
        # If "미보유" (Not Held & Sell/Observe), maybe score should reflect that?
        # User didn't specify Score changes for Holding status. "종목별 상세분석에서도 매수하고 있는 경우 매수 유지로 하고 ... " -> talking about Display.
        # But logic says "없는 종목의 경우 매수 신호가 나오면 매수".
        
        # Strategy:
        # 1. Calculate Technical Position (`tech_position`).
        # 2. Derive User Display Position (`user_position`) based on `is_held`.
        # 3. Use `tech_position` for Scoring? Or `user_position`?
        # If I have "미보유", it generally means "Do nothing".
        
        # Let's implement the User Rules for `position` string variable.
        
        tech_position = position
        
        if is_held:
            # Holding
            if "매도" in tech_position or "하단" in tech_position:
                 position = "🚨 매도"
            else:
                 # Buy, Buy Hold, Observe -> Maintain Buy
                 position = "🔵 매수 유지"
        else:
            # Check for specific signals to alert (User Request: Score >= 70 OR Entry/Breakout)
            # Note: 'score' is calculated later, so we need to use a placeholder or re-evaluate.
            # For now, we'll use the tech_position and assume score will be checked externally for alerts.
            # The instruction seems to imply this logic is for the *final* `position` string,
            # which is then used to derive `is_buy_signal` etc. for scoring.
            # However, the `score` itself is not available here yet.
            # Let's interpret the instruction as: if not held, only show "매수" if it's a strong technical buy signal (entry/breakout).
            # Otherwise, if it's a sell or observe, show "미보유".
            # The score >= 70 part is likely for the `monitor_signals` function in `main.py`
            # where the full `res` dictionary (including score) is available.
            
            # For `analyze_ticker`, we stick to the original logic for `position` based on `tech_position`
            # and let the `monitor_signals` function handle the score-based filtering.
            if "매수" in tech_position or "상단" in tech_position:
                 position = "🚨 매수"
            else:
                 # Sell, Sell Hold, Observe -> Not Held
                 position = "미보유"

            
        # Format Time
        formatted_signal_time = "-"
        if signal_time != "":
            try:
                # Handle Timezone
                st_target = signal_time
                if st_target.tzinfo is None:
                    st_target = st_target.replace(tzinfo=pytz.utc)
                
                st_kst = st_target.astimezone(pytz.timezone('Asia/Seoul'))
                formatted_signal_time = f"{st_kst.strftime('%m/%d %H:%M')} KST"
            except:
                formatted_signal_time = str(signal_time)

        macd = float(df_30['MACD'].iloc[-1])
        signal = float(df_30['Signal'].iloc[-1])
        rsi_val = float(df_30['RSI'].iloc[-1])
        
        news_prob = 50
        if rsi_val > 60: news_prob += 10
        if rsi_val < 40: news_prob -= 10
        if recent_cross_type == 'gold': news_prob += 20
        if recent_cross_type == 'dead': news_prob -= 20
        news_prob = max(0, min(100, news_prob))
        
        # === Cheongan Scoring Engine (User Rules) ===
        t30 = 'UP' if last_sma10 > last_sma30 else 'DOWN'
        t5 = 'UP' if last_5m_sma10 > last_5m_sma30 else 'DOWN'
        is_buy_signal = "매수" in position or "상단" in position
        is_sell_signal = "매도" in position or "하단" in position
        is_observing = not (is_buy_signal or is_sell_signal)


        base_main = 20 if not is_observing else 10
        base_confluence = 10 if t30 == t5 else -10
        
        # Auxiliary Indicators (Max 20)
        aux_rsi = 0
        aux_macd = 0
        aux_bb = 0
        aux_cross = 0
        
        bb_mid = float(df_30['BB_Mid'].iloc[-1])
        
        # (1) RSI (+5)
        if is_buy_signal or (is_observing and t30=='UP'):
            if 45 <= rsi_val <= 75: aux_rsi = 5
        elif is_sell_signal or (is_observing and t30=='DOWN'):
            if 25 <= rsi_val <= 55: aux_rsi = 5
            
        # (2) MACD (+5)
        if is_buy_signal or (is_observing and t30=='UP'):
            if macd > signal: aux_macd = 5
        elif is_sell_signal or (is_observing and t30=='DOWN'):
            if macd < signal: aux_macd = 5
            
        # (3) Bollinger Trend (+5)
        if is_buy_signal or (is_observing and t30=='UP'):
            if current_price > bb_mid: aux_bb = 5
        elif is_sell_signal or (is_observing and t30=='DOWN'):
            if current_price < bb_mid: aux_bb = 5
            
        # (4) Cross Type Match (+5)
        if (is_buy_signal and recent_cross_type == 'gold') or \
           (is_sell_signal and recent_cross_type == 'dead'):
            aux_cross = 5
            
        base_score = base_main + base_confluence + aux_rsi + aux_macd + aux_bb + aux_cross
        base_score = max(0, min(50, base_score))

        # 2. Trend Score
        # Signal Price & Bars
        sig_price = current_price
        bars_since = 0
        if cross_idx < 0: # Valid cross index
            try:
                sig_price = df_30['Close'].iloc[cross_idx]
                bars_since = abs(cross_idx)
            except:
                pass

        trend_score = 0
        if is_buy_signal and current_price > sig_price:
            trend_score = 10
        elif is_sell_signal and current_price < sig_price:
            trend_score = 10
        
        # 3. Reliability Score
        reliability_score = 0
        if not is_observing and bars_since >= 2:
            raw_diff_pct = ((current_price - sig_price) / sig_price) * 100
            profit_rate = raw_diff_pct if is_buy_signal else -raw_diff_pct
            
            if 1.5 <= profit_rate < 3.0:
                reliability_score = 5
            elif 3.0 <= profit_rate < 5.0:
                reliability_score = 8
            elif profit_rate >= 5.0:
                reliability_score = 5
            elif -5.0 < profit_rate <= -3.0:
                reliability_score = -3
            elif profit_rate <= -5.0:
                reliability_score = -7

        # 4. Breakout Score
        breakout_score = 0
        if not is_observing and bars_since >= 2:
            recent_12h = df_30.iloc[-24:]
            prev_12h_high = recent_12h['High'].iloc[:-1].max()
            prev_12h_low = recent_12h['Low'].iloc[:-1].min()
            
            if is_buy_signal and current_price >= prev_12h_high:
                breakout_score = 10
            elif is_sell_signal and current_price <= prev_12h_low:
                breakout_score = 10

        # 5. Market / Defensive Sell Score
        market_score = market_vol_score
        # [User Request] 박스권 불필요 매도 방지 로직
        if is_sell_signal:
            if market_vol_score < 5: market_score = -10
            if t5 == 'UP': market_score -= 10
            if is_box: market_score -= 20

        # PnL Score Adjustment
        pnl_impact = 0
        if is_held and is_sell_signal and holdings_data and ticker in holdings_data and isinstance(holdings_data[ticker], dict):
             avg_price = holdings_data[ticker].get('avg_price', 0)
             if avg_price > 0:
                 pnl_pct_held = ((current_price - avg_price) / avg_price) * 100
                 if pnl_pct_held > 0:
                     pnl_impact = pnl_pct_held * 5
                 else:
                     pnl_impact = abs(pnl_pct_held) * 10

        # Technical Sell Proposal Boost (+10)
        if is_sell_signal:
            bb_low = float(df_30['BB_Lower'].iloc[-1])
            if current_price < bb_low:
                pnl_impact += 10

        # 6. Total Score
        final_score = base_score + trend_score + reliability_score + breakout_score + market_score + pnl_impact
        final_score = int(max(0, min(100, final_score)))
        
        score_details = {
            "base": base_score,
            "base_details": {
                "main": base_main,
                "confluence": base_confluence,
                "rsi": aux_rsi,
                "macd": aux_macd,
                "bb": aux_bb,
                "cross": aux_cross
            },
            "trend": trend_score,
            "reliability": reliability_score,
            "breakout": breakout_score,
            "market": market_score,
            "pnl_adj": round(pnl_impact, 1),
            "total": final_score
        }

        # Change Pct (Only use historical fallback if Real-time info is missing)
        if not real_time_info:
            prev_close = df_30['Close'].iloc[-2] # Default fallback
            try:
                current_date = df_30.index[-1].date()
                prev_day_data = df_30[df_30.index.date < current_date]
                if not prev_day_data.empty:
                    prev_close = prev_day_data['Close'].iloc[-1]
                    change_pct = ((current_price - prev_close) / prev_close) * 100
            except:
                 pass

        # Generate Stock Specific Mock News (Technical)
        stock_news = []
        if recent_cross_type == 'gold': stock_news.append("골든크로스 발생: 강력한 매수 신호 포착")
        if recent_cross_type == 'dead': stock_news.append("데드크로스 발생: 매도 압력 증가")
        if is_box: stock_news.append("박스권 횡보 지속: 돌파 여부 모니터링 필요")
        if rsi_val > 70: stock_news.append("RSI 과매수권 진입: 차익 실현 매물 주의")
        elif rsi_val < 30: stock_news.append("RSI 과매도권 진입: 기술적 반등 기대감 유효")
        if change_pct > 3.0: stock_news.append(f"급등세 연출: 전일 대비 {change_pct:.1f}% 상승")
        elif change_pct < -3.0: stock_news.append(f"급락세 연출: 전일 대비 {abs(change_pct):.1f}% 하락")
        
        # Limit to 2
        if pnl_impact != 0:
            direction = "가점" if pnl_impact > 0 else "감점"
            stock_news.append(f"보유 수익률 반영: 점수 {abs(int(pnl_impact))}점 {direction}")
            
        # Limit to 2 (Prioritize PnL msg if exists)
        stock_news = stock_news[:2]
        if not stock_news: stock_news.append("특이사항 없음: 일반적인 시장 흐름 추종")

        result = {
            "ticker": ticker,
            "name": stock_name,
            "current_price": float(current_price) if pd.notnull(current_price) else None,
            "change_pct": float(change_pct) if pd.notnull(change_pct) else 0.0,
            "position": position,
            "last_cross_type": recent_cross_type,
            "signal_time": formatted_signal_time,
            "signal_time_raw": str(signal_time) if signal_time != "" else None, 
            "is_box": bool(is_box),
            "box_high": float(box_high) if pd.notnull(box_high) else 0.0,
            "box_low": float(box_low) if pd.notnull(box_low) else 0.0,
            "rsi": float(rsi_val) if pd.notnull(rsi_val) else None,
            "macd": float(macd) if pd.notnull(macd) else None,
            "macd_sig": float(signal) if pd.notnull(signal) else None,
            "prob_up": float(news_prob),
            "score": final_score,
            "score_interpretation": get_score_interpretation(final_score, position),
            "score_details": score_details,
            "news_items": stock_news,
            "is_held": is_held
        }
        return result
    
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return {"ticker": ticker, "name": stock_name, "error": str(e)}

def generate_market_insight(results, market_data):
    return insight

    return insight

def generate_trade_guidelines(results, market_data, regime_info, total_capital=10000.0, held_tickers={}):
    """
    Generate logic-based trade guidelines for Cheongan 2.0.
    Replaces generic news with actionable advice based on Holdings & Signals.
    Now includes Portfolio Rebalancing logic.
    """
    guidelines = []
    
    # 1. Market Regime & Capital Status
    regime = regime_info.get('regime', 'Sideways')
    regime_kr = "보합장(Sideways)"
    if regime == 'Bull': regime_kr = "상승장(Bull)"
    elif regime == 'Bear': regime_kr = "하락장(Bear)"
    
    # Calculate Capital Status
    current_holdings_value = 0.0
    for ticker, info in held_tickers.items():
        # info has {qty, avg_price}
        # Ideally use current price if available in results
        curr_price = info.get('avg_price', 0)
        # Find current price in results
        for r in results:
            if r['ticker'] == ticker:
                curr_price = r['current_price']
                break
        current_holdings_value += (info['qty'] * curr_price)
        
    cash_balance = total_capital - current_holdings_value
    cash_ratio = (cash_balance / total_capital) * 100 if total_capital > 0 else 0
    
    guidelines.append(f"현재 시장은 **{regime_kr}** 국면입니다.")
    guidelines.append(f"💰 **자산 현황**: 총 ${total_capital:,.0f} | 주식 ${current_holdings_value:,.0f} | 현금 ${cash_balance:,.0f} ({cash_ratio:.1f}%)")
    
    # 2. Holdings & Rebalancing Action Plan
    buy_candidates = []
    sell_candidates = []
    hold_maintenance = []
    
    # Map results to dict
    res_map = {r['ticker']: r for r in results}
    
    # Process Managed Stocks (Strategies)
    # We should iterate through results to find signals
    
    for res in results:
        ticker = res['ticker']
        pos = res.get('position', '')
        score = res.get('score', 0)
        curr_price = res.get('current_price', 0)
        strategy_info = res.get('strategy_info') # Passed from analyze_ticker? 
        # Actually analyze_ticker returns dict, but does it include strategy_info? 
        # No, analyze_ticker consumes it. We need access to target_ratio here?
        # Let's rely on what we can infer or fetch managed_stocks map here inside function if needed,
        # but better if result has 'target_ratio'.
        # Let's assume result has 'target_ratio' if we add it in analyze_ticker or merge it in run_analysis.
        # For now, let's use a quick lookup if passed or just generic logic if missing.
        
        target_ratio = res.get('target_ratio', 0) # Needs to be added to analyze_ticker return or run_analysis merge
        
        is_held = ticker in held_tickers
        held_qty = held_tickers[ticker]['qty'] if is_held else 0
        
        # ------------------------------------------------------------------
        # NEW: Inject Action Plan into Result Object for Frontend Table
        # ------------------------------------------------------------------
        res['held_qty'] = held_qty
        res['held_avg'] = held_tickers[ticker]['avg_price'] if is_held else 0
        res['target_ratio'] = target_ratio
        
        action_plan = "-"
        
        if "진입" in pos and "매수" in pos:
            # Calculate Recommended Buy Qty
            if target_ratio > 0 and curr_price > 0:
                target_amt = total_capital * (target_ratio / 100.0)
                current_amt = held_qty * curr_price
                needed_amt = target_amt - current_amt
                
                if needed_amt > 0:
                    buy_qty = int(needed_amt / curr_price)
                    if buy_qty > 0:
                        msg = f"{ticker}: "
                        if is_held:
                            avg = held_tickers[ticker]['avg_price']
                            msg += f"보유 {held_qty}주 → "
                        msg += f"**{buy_qty}주 추가 매수**"
                        buy_candidates.append(msg)
                        action_plan = f"추가 매수 {buy_qty}주 (목표 {target_ratio}%)"
                    else:
                        buy_candidates.append(f"{ticker}: 비중 충족")
                        action_plan = "현 비중 유지 (목표 달성)"
                else:
                     buy_candidates.append(f"{ticker}: 비중 충족")
                     action_plan = "현 비중 유지 (목표 달성)"
            else:
                 # No target ratio
                 buy_candidates.append(f"{ticker}: 신규 진입 (목표 미설정)")
                 action_plan = "신규 진입 (단타)"

        elif "진입" in pos and "매도" in pos:
             # Sell Logic
             msg = f"{ticker}: "
             if is_held:
                 avg = held_tickers[ticker]['avg_price']
                 msg += f"보유 {held_qty}주 → "
             msg += "**전량 매도**"
             sell_candidates.append(msg)
             action_plan = "전량 매도 권고"
             
        elif "유지" in pos:
             if is_held:
                 hold_maintenance.append(f"{ticker}: 보유 유지")
                 action_plan = f"보유 유지 ({held_qty}주)"
             else:
                 hold_maintenance.append(f"{ticker}: 관망")
                 action_plan = "관망"
        
        res['action_recommendation'] = action_plan
        # ------------------------------------------------------------------

    if buy_candidates:
        guidelines.append(f"✅ **매수 추천**: {', '.join(buy_candidates)}")
    
    if sell_candidates:
        guidelines.append(f"🚨 **매도 신호**: {', '.join(sell_candidates)}")
        
    if hold_maintenance:
        guidelines.append(f"🛡️ **보유/관망**: {', '.join(hold_maintenance)}")

    # 3. Strategy Tip
    if regime == 'Bull':
        guidelines.append("Tip: 상승장에서는 주도주(SOXL, IONQ) 비중을 꽉 채우고(Target %), 조정 시 추가 매수하십시오.")
    elif regime == 'Bear':
        guidelines.append("Tip: 하락장에서는 현금 비중 50% 이상 확보하고, 헷지(SOXS) 단타로 방어하십시오.")
    else:
        guidelines.append("Tip: 보합장에서는 박스권 매매(RSI 하단 매수/상단 매도)로 짧게 대응하십시오.")

    return "\n\n".join(guidelines)


def determine_market_regime(regime_daily, data_30m):
    
    regime = "Sideways" # Default
    regime_details = {}
    
    if regime_daily is not None and not regime_daily.empty:
        try:
            # UPRO
            upro_df = regime_daily['UPRO'].dropna() if 'UPRO' in regime_daily.columns.levels[0] else None
            # GSPC
            gspc_df = regime_daily['^GSPC'].dropna() if '^GSPC' in regime_daily.columns.levels[0] else None
            # IXIC
            ixic_df = regime_daily['^IXIC'].dropna() if '^IXIC' in regime_daily.columns.levels[0] else None
            
            is_bull = False
            is_bear = False
            
            # Helper for EMA 200 checks
            def check_ema200(df):
                if df is None or len(df) < 200: return False
                ema200 = calculate_ema(df['Close'], 200).iloc[-1]
                return df['Close'].iloc[-1] > ema200
            
            # --- Bull Condition ---
            # S&P500(UPRO) > EMA 200 & NASDAQ > EMA 200
            # AND 30m SMA 10 > 30 (Check SPY/QQQ 30m? Let's use UPRO 30m from data_30m)
            
            bull_daily = check_ema200(upro_df) and check_ema200(ixic_df)
            
            # Check 30m alignment for Bull
            bull_30m = False
            if 'UPRO' in data_30m.columns.levels[0]:
                upro_30 = data_30m['UPRO'].dropna()
                if not upro_30.empty:
                     upro_30['SMA10'] = calculate_sma(upro_30['Close'], 10)
                     upro_30['SMA30'] = calculate_sma(upro_30['Close'], 30)
                     if upro_30['SMA10'].iloc[-1] > upro_30['SMA30'].iloc[-1]:
                         bull_30m = True
            
            if bull_daily and bull_30m:
                is_bull = True
                
            # --- Bear Condition ---
            # Close < EMA 200 (Daily) OR Weekly Drop > -5%
            # Check UPRO or GSPC? Using GSPC for broader market Bear check
            bear_daily = not check_ema200(gspc_df)
            
            # Weekly Drop
            weekly_drop = False
            if gspc_df is not None and len(gspc_df) > 5:
                curr = gspc_df['Close'].iloc[-1]
                week_ago = gspc_df['Close'].iloc[-5]
                drop_pct = ((curr - week_ago) / week_ago) * 100
                if drop_pct < -5.0:
                    weekly_drop = True
            
            if bear_daily or weekly_drop:
                is_bear = True
            
            # --- Sideways Condition ---
            # ADX(14) < 20 OR 5-day Range < 1.5 * ATR(14)
            is_sideways = False
            if upro_df is not None:
                adx_series = calculate_adx(upro_df)
                adx_val = adx_series.iloc[-1]
                
                atr_series = calculate_atr(upro_df)
                atr_val = atr_series.iloc[-1]
                
                # 5-day range
                recent_5 = upro_df.iloc[-5:]
                range_5 = recent_5['High'].max() - recent_5['Low'].min()
                
                if adx_val < 20 or range_5 < (1.5 * atr_val):
                    is_sideways = True
            
            # Decision Priority: Bear > Bull > Sideways (Defensive first?)
            # User Scenario: Bull, Bear, Sideways. 
            # If conflicts? Bear signals are usually critical (Safety).
            if is_bull: regime = "Bull"
            elif is_bear: regime = "Bear"
            elif is_sideways: regime = "Sideways"
            else: regime = "Sideways" # Default fallback
            
            regime_details = {
                "bull_cond": f"Daily>EMA200:{bull_daily}, 30mUp:{bull_30m}",
                "bear_cond": f"Daily<EMA200:{bear_daily}, WeeklyDrop:{weekly_drop}",
                "side_cond": f"ADX<20:{is_sideways}"
            }
            
        except Exception as e:
            print(f"Regime Analysis Error: {e}")
            regime = "Sideways" # Safe default

    # Update DB with Regime
    try:
        from db import update_market_status
        update_market_status(regime, regime_details)
    except Exception as e:
        print(f"DB Update Market Status Error: {e}")

    return {"regime": regime, "details": regime_details}


def run_analysis(held_tickers=[]):
    print("Starting Analysis Run...")
    
    # -------------------------------------------------------------
    # DYNAMIC TICKER FETCHING (Cheongan 2.0)
    # -------------------------------------------------------------
    from db import get_managed_stocks, get_total_capital, get_current_holdings, update_market_status
    from kis_api import kis_client  # Import singleton instance
    
    # Exchange Mapping for Speed (Avoid 3 sequential requests)
    # Ideally should be in database or global config, but keeping here for now.
    EXCHANGE_MAP_KIS = {
        "TSLA": "NAS", "GOOGL": "NAS", "AMZU": "NAS", "UFO": "NAS", "NVDA": "NAS", "AAPL": "NAS", "MSFT": "NAS", "AMZN": "NAS", "NFLX": "NAS", "AMD": "NAS", "INTC": "NAS", "QQQ": "NAS", "TQQQ": "NAS", "SQQQ": "NAS", "XPON": "NAS",
        "SOXL": "NYS", "SOXS": "NYS", "UPRO": "NYS", "AAAU": "NYS", "IONQ": "NYS", "SPY": "NYS", "IVV": "NYS", "VOO": "NYS"
    }
    
    managed_stocks_list = get_managed_stocks()
    if not managed_stocks_list:
        print("Warning: No managed stocks found in DB. Using default fallback.")
        db_tickers = []
    else:
        db_tickers = [s['ticker'] for s in managed_stocks_list]
        print(f"Loaded {len(db_tickers)} tickers from DB: {db_tickers}")

    # Use DB tickers if available, else fallback to hardcoded
    # Assuming TARGET_TICKERS is defined globally or imported from another module
    # If not, it needs to be defined here as a default.
    # For this context, let's assume TARGET_TICKERS is available from the original file's scope.
    global TARGET_TICKERS, TICKER_NAMES # Declare global if they are defined outside this function
    
    active_tickers = db_tickers if db_tickers else TARGET_TICKERS
    
    # Update TICKER_NAMES map if possible (optional but good for display)
    if managed_stocks_list:
        for s in managed_stocks_list:
            t_ticker = s.get('ticker')
            if t_ticker:
                TICKER_NAMES[t_ticker] = s.get('name', t_ticker)
            
    # -------------------------------------------------------------

    # 1. Fetch Market Data
    # Only fetch active tickers + indicators
    # The original fetch_data() returned data_30m, data_5m, market_data, regime_daily
    # We need to ensure fetch_market_data returns what's needed for determine_market_regime
    # Let's adjust fetch_data to return all necessary components.
    # Assuming fetch_data() is modified to take active_tickers and return all necessary dataframes.
    data_30m, data_5m, data_1d, market_data, regime_daily_data = fetch_data(active_tickers) # Assuming fetch_data now takes tickers
    
    # 2. Determine Market Regime
    # Pass the relevant daily data for regime analysis.
    # Assuming regime_daily_data contains UPRO, GSPC, IXIC daily data.
    regime_info = determine_market_regime(regime_daily_data, data_30m)
    
    # Calculate Market Volatility Score (using market_data from fetch_data)
    market_vol_score = -5 # Default: Neutral/Flat (Bad? User says High Volatility is Good (+5))
    # User: "보합/혼조세면 -5점 , 강한 상승장이나 하락장이면 +5점"
    
    if "S&P500" in market_data:
        df_spy = market_data["S&P500"]
        if not df_spy.empty and len(df_spy) >= 2:
            # Check 1 day change
            curr = df_spy['Close'].iloc[-1]
            prev = df_spy['Close'].iloc[-2]
            spy_change = ((curr - prev) / prev) * 100
            
            if abs(spy_change) >= 0.5:
                market_vol_score = 5
    
    # 3. Analyze Tickers (Real-time KIS Price Fetching)
    real_time_map = {}
    real_time_map = {}
    try:
        # kis_client imported from kis_api is already instantiated
        pass
        
        def fetch_wrapper(t):
             excd = EXCHANGE_MAP_KIS.get(t)
             return t, kis_client.get_price(t, exchange=excd)
        
        # Increase workers slightly as we have fast timeout
        with ThreadPoolExecutor(max_workers=8) as executor:
             futs = [executor.submit(fetch_wrapper, t) for t in active_tickers]
             # Add total timeout for entire batch to prevent hanging
             # We rely on individual timeouts (1.5s)
             for f in futs:
                 try:
                     t, info = f.result(timeout=4) # Max wait per task
                     if info: real_time_map[t] = info
                 except: pass

    except Exception as e:
        print(f"KIS Price Fetch Error: {e}")

    results = []
    
    # Fetch Managed Stocks Strategies (Already fetched above but need map)
    managed_map = {s['ticker']: s for s in managed_stocks_list}
    
    # Fetch Holdings & Capital
    held_tickers = get_current_holdings()
    total_capital = get_total_capital()

    for ticker in active_tickers:
        is_held = ticker in held_tickers
        rt_info = real_time_map.get(ticker)
        
        # Cheongan 2.0: Pass Strategy Info
        strategy_info = managed_map.get(ticker, None)
        
        # held_tickers is the dict from db.get_current_holdings
        res = analyze_ticker(ticker, data_30m, data_5m, data_1d, market_vol_score, is_held, real_time_info=rt_info, holdings_data=held_tickers, strategy_info=strategy_info)
        
        # Attach strategy target ratio logic (Cheongan 2.1 Regime-based)
        if strategy_info:
            regime = regime_info.get('regime', 'Sideways')
            base_target = strategy_info.get('target_ratio', 0)
            group_name = strategy_info.get('group_name', '')
            final_target = base_target
            
            # Regime Adjustment
            if regime == 'Bear':
                if ticker == 'SOXS': 
                     final_target = 20 # Active Hedge
                elif '헷지' in group_name or '안정성' in group_name:
                     final_target = base_target
                else:
                     final_target = int(base_target * 0.3) # Heavy cut on Growth
            elif regime == 'Bull':
                final_target = base_target
                if ticker == 'SOXS': final_target = 0
            else: # Sideways
                if ticker == 'SOXS': final_target = 5
                else: final_target = int(base_target * 0.8)

            res['target_ratio'] = final_target
            res['base_target'] = base_target
            
        results.append(res)
        
    # Get Market Indicators Data with Change %
    indicators = {}
    for name, df in market_data.items():
        try:
            val = 0.0
            change = 0.0
            if not df.empty and 'Close' in df.columns:
                val = df['Close'].iloc[-1]
                if len(df) >= 2:
                    prev = df['Close'].iloc[-2]
                    change = ((val - prev) / prev) * 100
            
            indicators[name] = {
                "value": float(val) if val is not None and pd.notnull(val) else 0.0,
                "change": float(change) if change is not None and pd.notnull(change) else 0.0
            }
            
        except Exception as e:
             indicators[name] = {"value": 0.0, "change": 0.0}

    # Fetch Regime Info from DB
    regime_info = {"regime": "Sideways", "details": {}}
    try:
        from db import get_latest_market_status, get_total_capital
        last_stat = get_latest_market_status()
        if last_stat:
            regime_info = {
                "regime": last_stat['regime'],
                "details": last_stat['details'],
                "updated_at": str(last_stat['updated_at'])
            }
        
        # Fetch Total Capital
        total_cap = get_total_capital()
        
    except: 
        total_cap = 10000.0
        pass

    # Generate Trade Guidelines (Was Insight)
    insight_text = generate_trade_guidelines(results, market_data, regime_info, total_cap, held_tickers)

    return {
        "timestamp": get_current_time_str(),
        "stocks": results,
        "market": indicators,
        "insight": insight_text,
        "market_regime": regime_info
    }

if __name__ == "__main__":
    # Test run
    print(run_analysis())
