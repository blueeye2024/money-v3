import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import pytz
import os
import time
import re
from concurrent.futures import ThreadPoolExecutor
from kis_api import kis_client

# Global Cache for Historical Data
_DATA_CACHE = {
    "30m": None,
    "5m": None,
    "1d": None,
    "market": None,
    "regime": None,
    "last_fetch_realtime": 0,
    "last_fetch_longterm": 0
}


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

def is_market_open():
    """Checks if US Market is currently open (Regular Hours)"""
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(timezone.utc).astimezone(est)
    
    # Check Weekend
    if now_est.weekday() >= 5: return False
    
    # Regular Hours: 09:30 - 16:00
    market_start = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    market_end = now_est.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_start <= now_est <= market_end

def fetch_data(tickers=None):
    global _DATA_CACHE
    
    target_list = tickers if tickers else TARGET_TICKERS
    now = time.time()
    
    # 1. Tiered Fetching Logic
    # check real-time (30m, 5m): 1 min
    needs_realtime = (now - _DATA_CACHE.get("last_fetch_realtime", 0)) > 60
    # check long-term (1d, indices): 10 min
    needs_longterm = (now - _DATA_CACHE.get("last_fetch_longterm", 0)) > 600
    
    # If using default tickers and everything is fresh, return cache
    if tickers is None and not needs_realtime and _DATA_CACHE["30m"] is not None:
        return _DATA_CACHE["30m"], _DATA_CACHE["5m"], _DATA_CACHE.get("1d"), _DATA_CACHE["market"], _DATA_CACHE.get("regime")

    # 2. Incremental Data Fetch & DB Update
    if needs_realtime or tickers is not None:
        try:
            from db import save_market_candles, load_market_candles
            
            # Decide fetch period (Incremental or Init)
            fetch_period = "5d" # Default small window for incremental update
            
            # Check if we need initialization (check SOXL)
            chk_df = load_market_candles("SOXL", "30m", limit=1)
            if chk_df is None or chk_df.empty:
                print("🚀 Initializing DB: Fetching 1 month of history...")
                fetch_period = "1mo"
            
            tickers_str = " ".join(target_list)
            print(f"Fetching Real-time (30m, 5m) Period={fetch_period}...")
            
            # Fetch from yfinance
            new_30m = yf.download(tickers_str, period=fetch_period, interval="30m", prepost=True, group_by='ticker', threads=True, progress=False, timeout=20)
            new_5m = yf.download(tickers_str, period=fetch_period, interval="5m", prepost=True, group_by='ticker', threads=True, progress=False, timeout=20)
            
            # Save to DB (Upsert) - Only Core Tickers
            CORE_TICKERS = ["SOXL", "SOXS", "UPRO"]
            from db import cleanup_old_candles

            for ticker in target_list:
                # Optimized: Only save history for core tickers to DB
                if ticker not in CORE_TICKERS: continue

                # 30m Save
                try:
                    df = None
                    if isinstance(new_30m.columns, pd.MultiIndex) and ticker in new_30m.columns: df = new_30m[ticker]
                    elif not isinstance(new_30m.columns, pd.MultiIndex) and len(target_list) == 1: df = new_30m
                    if df is not None and not df.empty: 
                        save_market_candles(ticker, '30m', df, 'yfinance')
                        cleanup_old_candles(ticker, days=60) # Auto cleanup
                except Exception as e: print(f"Save 30m Error {ticker}: {e}")

                # 5m Save
                try:
                    df = None
                    if isinstance(new_5m.columns, pd.MultiIndex) and ticker in new_5m.columns: df = new_5m[ticker]
                    elif not isinstance(new_5m.columns, pd.MultiIndex) and len(target_list) == 1: df = new_5m
                    if df is not None and not df.empty: 
                        save_market_candles(ticker, '5m', df, 'yfinance')
                        cleanup_old_candles(ticker, days=30) # 5m data is heavy, keep 30 days
                except Exception as e: print(f"Save 5m Error {ticker}: {e}")
            
            _DATA_CACHE["last_fetch_realtime"] = now
            
        except Exception as e:
            print(f"Incremental Fetch Error: {e}")
            
    # Always Load from DB (Single Source of Truth)
    # This acts as both Cache Hit and Fallback
    try:
        from db import load_market_candles
        cache_30m = {}
        cache_5m = {}
        
        for ticker in target_list:
            df30 = load_market_candles(ticker, "30m", limit=300)
            df5 = load_market_candles(ticker, "5m", limit=300)
            if df30 is not None: cache_30m[ticker] = df30
            if df5 is not None: cache_5m[ticker] = df5
            
        if cache_30m: _DATA_CACHE["30m"] = cache_30m
        if cache_5m: _DATA_CACHE["5m"] = cache_5m
        
        print(f"✅ Loaded {len(cache_30m)} tickers from DB Cache")
        
        # KIS Live Patching
        try:
            from kis_api import kis_client
            EXCHANGE_MAP = {"SOXL": "NYS", "SOXS": "NYS", "UPRO": "NYS", "IONQ": "NYS"}
            for ticker in ["SOXL", "SOXS", "UPRO"]:
                if ticker in cache_30m or ticker in cache_5m:
                    kis = kis_client.get_price(ticker, exchange=EXCHANGE_MAP.get(ticker))
                    if kis and kis['price'] > 0:
                        if ticker in cache_30m: cache_30m[ticker].iloc[-1, cache_30m[ticker].columns.get_loc('Close')] = kis['price']
                        if ticker in cache_5m: cache_5m[ticker].iloc[-1, cache_5m[ticker].columns.get_loc('Close')] = kis['price']
                        print(f"  💹 {ticker} KIS UPDATE: {kis['price']}")
        except Exception as e: print(f"KIS Patch Error: {e}")
        
    except Exception as e:
        print(f"DB Load Error: {e}")

    # 3. Long-term Data Fetch (1d, Market, Regime)
    if needs_longterm or _DATA_CACHE.get("1d") is None:
        try:
            tickers_str = " ".join(target_list)
            print("Fetching Long-term (1d) for Stocks...")
            new_1d = yf.download(tickers_str, period="6mo", interval="1d", group_by='ticker', threads=False, progress=False, timeout=10)
            if not new_1d.empty: _DATA_CACHE["1d"] = new_1d
            
            print("Fetching market data (Indices)...")
            market_data = {}
            for name, tic_sym in MARKET_INDICATORS.items():
                t = yf.Ticker(tic_sym)
                hist = t.history(period="5d")
                if not hist.empty: market_data[name] = hist
                elif _DATA_CACHE.get("market") and name in _DATA_CACHE["market"]:
                    market_data[name] = _DATA_CACHE["market"][name]
            _DATA_CACHE["market"] = market_data

            print("Fetching Daily data for Market Regime...")
            reg_tickers = ["UPRO", "^GSPC", "^IXIC", "SPY"]
            new_regime = yf.download(reg_tickers, period="6mo", interval="1d", group_by='ticker', threads=False, progress=False, timeout=10)
            if not new_regime.empty: _DATA_CACHE["regime"] = new_regime
            
            _DATA_CACHE["last_fetch_longterm"] = now
        except Exception as e:
            print(f"Long-term Fetch Error: {e}")

    # Final Robustness: If something is still None, return structure with cached/empty
    d30 = _DATA_CACHE.get("30m") if _DATA_CACHE.get("30m") is not None else pd.DataFrame()
    d5 = _DATA_CACHE.get("5m") if _DATA_CACHE.get("5m") is not None else pd.DataFrame()
    d1 = _DATA_CACHE.get("1d") if _DATA_CACHE.get("1d") is not None else pd.DataFrame()
    m = _DATA_CACHE.get("market") if _DATA_CACHE.get("market") is not None else {}
    reg = _DATA_CACHE.get("regime") if _DATA_CACHE.get("regime") is not None else pd.DataFrame()
    
    return d30, d5, d1, m, reg

def calculate_sma(series, window):
    return series.rolling(window=window).mean()

def calculate_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_score_interpretation(score, position):
    if "매수" in position:
        if score >= 80: return "강력 매수 분출"
        if score >= 60: return "매수 우위 지속"
        return "신중한 매수"
    elif "매도" in position:
        if score >= 80: return "급격한 투매 주의"
        if score >= 60: return "매도 압력 강함"
        return "기술적 매도 구간"
    else:
        if score >= 70: return "강한 반등 대기"
        if score >= 40: return "박스권 횡보"
        return "심리적 위축"

def check_box_pattern(df_30m, days=7, tolerance=5.0):
    """
    Check box pattern with flexible tolerance.
    Returns: (is_box, high_val, low_val, pct_diff)
    """
    if df_30m.empty: return False, 0, 0, 0
    try:
        # Use last N 30-min candles
        n_candles = int(days * 13) 
        sub = df_30m.tail(n_candles)
        h = sub['High'].max()
        l = sub['Low'].min()
        diff = ((h - l) / l) * 100 if l > 0 else 0
        return diff <= tolerance, h, l, diff
    except: return False, 0, 0, 0

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
        df_30['RSI'] = calculate_rsi(df_30['Close'], 14)

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
            # rate is percentage change
            change_pct = float(real_time_info['rate'])
        elif (kp := kis_client.get_price(ticker)):
             current_price = kp['price']
             change_pct = kp['rate']
        
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
            position = "🔴 매수 진입" if cross_idx == -1 else "🔴 매수 유지" if valid else "관망 (매수 신호 무효화)"
        elif recent_cross_type == 'dead':
            if last_5m_sma10 > last_5m_sma30: valid = False
            if is_box:
                 if current_price < box_low: pass
                 else: valid = False
            position = "🔹 매도 진입" if cross_idx == -1 else "🔵 매도 유지" if valid else "관망 (매도 신호 무효화)"
            
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
                 position = "🔹 매도"
            else:
                 # Buy, Buy Hold, Observe -> Maintain Buy
                 position = "🔴 매수 유지"
        else:
            # Check for specific signals to alert
            if "매수" in tech_position or "상단" in tech_position:
                 position = "🔴 매수"
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
            "signal_time_raw": signal_time.strftime('%Y-%m-%d %H:%M:%S') if signal_time != "" else None, 
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
            "is_held": is_held,
            "strategy_result": strategy_desc
        }
        return result
    
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return {"ticker": ticker, "name": stock_name, "error": str(e)}

def generate_market_insight(results, market_data):
    return insight

    return insight

def generate_trade_guidelines(results, market_data, regime_info, total_capital=10000.0, held_tickers={}, krw_rate=1460.0):
    """
    Generate logic-based trade guidelines for Cheongan 2.1.
    """
    guidelines = []
    
    # 1. Market Regime & Capital Status
    regime = regime_info.get('regime', 'Sideways')
    details = regime_info.get('details', {})
    reason = details.get('reason', '시장 데이터 분석 중')
    
    regime_kr = f"{regime}: {reason}"
    
    if regime == 'Bull': 
        strategy_summary = "공격적 매수 (SOXL/UPRO/TSLA/IONQ/현금15%)"
    elif regime == 'Bear': 
        strategy_summary = "인버스 수익 및 안전자산 대피 (SOXS/TMF/AAAU/현금20%)"
    else:
        strategy_summary = "자산 방어 및 현금 대기 (AAAU/GOOGL/현금50%)"
    
    # Calculate Capital Status
    current_holdings_value = 0.0
    for ticker, info in held_tickers.items():
        curr_price = info.get('avg_price', 0)
        # Find current price in results
        for r in results:
            if r['ticker'] == ticker:
                curr_price = r.get('current_price', 0)
                break
        current_holdings_value += (info['qty'] * curr_price)
        
    cash_balance = total_capital - current_holdings_value
    
    # Asset Object for Frontend Header
    total_assets = {
        "usd": total_capital,
        "krw": total_capital * krw_rate,
        "cash_usd": cash_balance,
        "cash_krw": cash_balance * krw_rate,
        "stock_usd": current_holdings_value,
        "stock_krw": current_holdings_value * krw_rate
    }
    
    guidelines.append(f"### 📡 시장 국면: **{regime_kr}**")
    guidelines.append(f"🔍 **판단 사유**: {reason}")
    guidelines.append(f"📋 **핵심 전략**: {strategy_summary}")
    # Total Asset line removed (Moved to Top Header)
    
    guidelines.append("\n**[종목별 리밸런싱 실행 가이드]**")
    
    # 2. Rebalancing Action Plan
    actions = []
    
    for res in results:
        ticker = res['ticker']
        target_ratio = res.get('target_ratio', 0)
        action_qty = res.get('action_qty', 0)
        held_qty = res.get('held_qty', 0)
        
        action_str = "-"
        
        if target_ratio == 0 and held_qty > 0:
             action_str = f"🛑 전량 매도 (-{held_qty})"
             actions.append(f"- **{ticker}**: {action_str} (전략 제외 종목)")
             res['action_qty'] = -held_qty
             
        elif action_qty > 0:
             action_str = f"➕ {action_qty}주 매수"
             actions.append(f"- **{ticker}**: {action_qty}주 추가 매수 (목표 {target_ratio}%)")
             
        elif action_qty < 0:
             sell_q = abs(action_qty)
             action_str = f"➖ {sell_q}주 매도"
             actions.append(f"- **{ticker}**: {sell_q}주 부분 매도 (비중 축소)")
             
        elif held_qty > 0:
             action_str = "✅ 유지"
             
        elif target_ratio > 0 and held_qty == 0:
             action_str = "관망/진입대기"
        
        res['action_recommendation'] = action_str
        
    if actions:
        guidelines.extend(actions)
    else:
        guidelines.append("- 특이사항 없음 (현재 포트폴리오 목표 비중 유지 중)")

    # NEW: Build Strategic Portfolio Data for Frontend (Left Side)
    strategy_list = []
    for res in results:
        t_w = res.get('target_ratio', 0)
        if t_w > 0:
            p = res.get('current_price', 0)
            req_q = int((total_capital * (t_w/100.0)) / p) if p > 0 else 0
            req_amt = req_q * p
            strategy_list.append({
                "ticker": res['ticker'], 
                "weight": t_w, 
                "price": p, 
                "req_qty": req_q,
                "req_amt_usd": req_amt,
                "req_amt_krw": req_amt * krw_rate,
                "held_qty": res.get('held_qty', 0)
            })
    
    # Cash Target
    # Cash Target
    cash_w = 50 # Sideways Trap default
    if regime == 'Bull': cash_w = 15
    elif regime == 'Bear': cash_w = 20
    
    curr_cash = total_capital - current_holdings_value
    target_cash_amt = total_capital * (cash_w/100.0)
    
    strategy_list.append({
        "ticker": "CASH",
        "weight": cash_w,
        "price": 1.0,
        "req_qty": int(target_cash_amt),
        "req_amt_usd": target_cash_amt,
        "req_amt_krw": target_cash_amt * krw_rate,
        "held_qty": int(curr_cash)
    })
    
    strategy_list.sort(key=lambda x: x['weight'], reverse=True)

    return "\n".join(guidelines), strategy_list, total_assets


# Legacy regime functions removed.


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
    
    # 2. Determine Market Regime (V2.3 Master Signal)
    regime_info = determine_market_regime_v2(regime_daily_data, data_30m, data_5m)
    
    # Calculate Market Volatility Score (V2.3: Replaced by Master Signals, but keeping variable for compatibility)
    market_vol_score = 5 if regime_info.get('regime') in ['Bull', 'Bear'] else -5
    
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
        try:
            is_held = ticker in held_tickers
            rt_info = real_time_map.get(ticker)
            
            # Cheongan 2.0: Pass Strategy Info
            strategy_info = managed_map.get(ticker, None)
            
            # held_tickers is the dict from db.get_current_holdings
            res = analyze_ticker(ticker, data_30m, data_5m, data_1d, market_vol_score, is_held, real_time_info=rt_info, holdings_data=held_tickers, strategy_info=strategy_info)
            
            # --- V2.3 SYNC LOGIC OVERRIDE ---
            regime = regime_info.get('regime', 'Sideways')
            
            sync_categories = {
                "High_Beta": ["SOXL", "UPRO", "IONQ"],
                "Growth": ["TSLA", "GOOGL"],
                "Defensive": ["SOXS", "TMF", "AAAU"],
                "Other": ["UFO", "AMZU"]
            }
            
            if regime == "Bull": # SOXL FINAL_BUY (Risk-On)
                if ticker in sync_categories["High_Beta"]:
                    if "매도" in res['position'] or "미보유" in res['position']:
                        res['position'] = "🔴 적극 매수 (Master Sync)"
                elif ticker in sync_categories["Growth"]:
                    res['position'] = "🔴 매수 유지 (Master Sync)"
                elif ticker in sync_categories["Other"]:
                    res['position'] = "⚪ 보유 (Master Sync)"
                elif ticker in sync_categories["Defensive"]:
                    res['position'] = "🔹 전량 매도 (Master Sync)"
                    
            elif regime == "Bear": # SOXS FINAL_BUY (Risk-Off)
                if ticker in sync_categories["Defensive"]:
                    if "매도" in res['position'] or "미보유" in res['position']:
                        res['position'] = "🔴 적극 매수 (Master Sync)"
                elif ticker in sync_categories["High_Beta"]:
                    res['position'] = "🔹 전량 매도 (Master Sync)"
                elif ticker in sync_categories["Growth"]:
                    res['position'] = "🔹 비중 축소 (Master Sync)"
                elif ticker in sync_categories["Other"]:
                    res['position'] = "🔹 매도 (Master Sync)"
            
            # Inject Holding Info for Frontend (Cheongan 2.1)
            if ticker in held_tickers:
                 res['held_qty'] = held_tickers[ticker]['qty']
                 res['avg_price'] = held_tickers[ticker]['avg_price']
            else:
                 res['held_qty'] = 0
                 res['avg_price'] = 0
            
            # Error Handling: Ensure keys exist
            if "error" in res:
                res.setdefault('current_price', 0)
                res.setdefault('change_pct', 0)
                res.setdefault('score', 0)
                res.setdefault('position', 'Error')

            # Attach strategy target ratio logic (Cheongan 2.1 Regime-based)
            if strategy_info:
                regime = regime_info.get('regime', 'Sideways')
                base_target = strategy_info.get('target_ratio', 0)
                group_name = strategy_info.get('group_name', '')
                final_target = base_target
                
                # Cheongan 2.1: Advanced Regime Portfolio Matrix (User Definied)
                t_map = {
                    'Bull': {
                        'SOXL': 25, 'UPRO': 20, 'TSLA': 20, 'IONQ': 20,
                        'GOOGL': 0, 'AAAU': 0, 'TMF': 0, 'SOXS': 0, 'UFO': 0
                    },
                    'Sideways': {
                        'AAAU': 30, 'GOOGL': 20,
                        'SOXL': 0, 'UPRO': 0, 'TSLA': 0, 'IONQ': 0, 'SOXS': 0, 'TMF': 0, 'UFO': 0
                    },
                    'Bear': {
                        'SOXS': 35, 'TMF': 25, 'AAAU': 20,
                        'SOXL': 0, 'UPRO': 0, 'TSLA': 0, 'IONQ': 0, 'GOOGL': 0, 'UFO': 0
                    }
                }
                
                # Disable Regime-based Filtering (User Request: Show All)
                # if ticker in t_map.get(regime, {}): ...
                
                final_target = base_target

    
                res['target_ratio'] = final_target
                res['base_target'] = base_target
                res['strategy_text'] = strategy_info.get('buy_strategy', '-')
                
                # Calculate Action Qty & Current Ratio
                curr_p = res.get('current_price', 0)
                held_q = res.get('held_qty', 0)
                
                if curr_p and curr_p > 0 and total_capital > 0:
                    current_val = held_q * curr_p
                    current_ratio = (current_val / total_capital) * 100
                    
                    target_val = total_capital * (final_target / 100.0)
                    diff_val = target_val - current_val
                    
                    action_qty = int(diff_val / curr_p)
                    res['action_est_cost'] = action_qty * curr_p
                else:
                    current_ratio = 0
                    action_qty = 0
                    res['action_est_cost'] = 0
                    
                res['current_ratio'] = current_ratio
                res['action_qty'] = action_qty # Positive = Buy, Negative = Sell
                
            results.append(res)
        
        except Exception as e:
            print(f"Critical Analysis Loop Error for {ticker}: {e}")
             # Add detailed error result to prevent frontend crash
            results.append({
                "ticker": ticker, 
                "name": ticker, 
                "error": str(e),
                "current_price": 0,
                "change_pct": 0,
                "score": 0,
                "position": "SysError"
            })
        
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

    # Fetch Total Capital
    try:
        from db import get_total_capital
        total_cap = get_total_capital()
    except:
        total_cap = 10000.0

    # Generate Trade Guidelines (Was Insight)
    insight_text, strategy_list, total_assets = generate_trade_guidelines(results, market_data, regime_info, total_cap, held_tickers)

    # Calculate Market Volatility Score (V2.3: Replaced by Master Signals, but keeping variable for compatibility)
    market_vol_score = 5 if regime_info.get('regime') in ['Bull', 'Bear'] else -5

    # --- JSON CLEANUP (Remove NaN) ---
    def clean_nan(obj):
        if isinstance(obj, list):
            return [clean_nan(i) for i in obj]
        elif isinstance(obj, dict):
            return {k: clean_nan(v) for k, v in obj.items()}
        elif isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
            return 0.0
        return obj

    final_results = clean_nan(results)
    final_indicators = clean_nan(indicators)
    final_regime = clean_nan(regime_info)

    return {
        "timestamp": get_current_time_str(),
        "stocks": final_results,
        "market": final_indicators,
        "insight": insight_text,
        "strategy_list": clean_nan(strategy_list),
        "total_assets": clean_nan(total_assets),
        "market_regime": final_regime
    }

# --- 2026 Project: New Regime Logic V2 ---
# --- 2026 Project: New Regime Logic V2 ---
def analyze_30m_box(df_30m):
    try:
        if df_30m is None or len(df_30m) < 60:
            return "INSUFFICIENT_DATA", 0.0, 0.0, 0.0
        recent_bars = df_30m.tail(60)
        # Ensure High/Low exist
        if 'High' not in recent_bars.columns: return "ERROR_COLS", 0,0,0
        
        box_high = recent_bars['High'].max()
        box_low = recent_bars['Low'].min()
        current_price = df_30m['Close'].iloc[-1]
        
        if box_low == 0: return "ERROR_ZERO", 0,0,0
        
        box_width_pct = (box_high - box_low) / box_low * 100
        
        status = "TRENDING_UNDEFINED"
        if current_price > box_high * 1.003: status = "BOX_BREAKOUT_UP"
        elif current_price < box_low * 0.997: status = "BOX_BREAKDOWN_DOWN"
        elif box_width_pct < 3.0: status = "BOX_SIDEWAYS"
        
        return status, box_high, box_low, box_width_pct
    except: return "ERROR_EXCEPTION", 0,0,0


def get_us_reg_close(df):
    """Find the last close price from US regular hours (09:30-16:00 ET) before current day"""
    try:
        if df.empty: return None
        # Convert index to ET
        df_et = df.copy()
        df_et.index = df_et.index.tz_convert('US/Eastern')
        
        # Filter for regular hours (9:30 to 16:00)
        reg_hours = df_et.between_time('09:30', '16:00')
        if reg_hours.empty: return None
        
        # Get last date in reg_hours
        last_date = reg_hours.index[-1].date()
        # Find the close of the last bar of the PREVIOUS regular trading day
        prev_reg_days = reg_hours[reg_hours.index.date < last_date]
        if prev_reg_days.empty:
            # If only one day in data, return the first available reg hour close as fallback
            return float(reg_hours['Close'].iloc[-1])
            
        prev_date = prev_reg_days.index[-1].date()
        prev_day_close = prev_reg_days[prev_reg_days.index.date == prev_date]['Close'].iloc[-1]
        return float(prev_day_close)
    except:
        return None

def check_triple_filter(ticker, data_30m, data_5m):
    print("FUNCTION ENTERED check_triple_filter")
    """
    Cheongan V2.5 Master Filter Logic
    Order: Step 1 (5m Timing), Step 2 (30m Trend), Step 3 (2% Strength)
    - Step 2 (30m) is "Sticky": Once met, stays True until Dead Cross.
    - Tracks completion time/price for each step.
    """
    from db import get_global_config, set_global_config
    
    result = {
        "step1": False, "step2": False, "step3": False, "final": False, 
        "step1_color": None, "step2_color": None, "step3_color": None,
        "target": 0, "signal_time": None, "is_sell_signal": False,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "step_details": {
            "step1": "대기 중", "step2": "대기 중", "step3": "대기 중"
        },
        "current_price": 0.0,
        "daily_change": 0.0,
        "entry_price": 0.0
    }
    
    # Fallback Data (Safe UI Rendering when API fails)
    if ticker == "SOXL":
        result["current_price"] = 42.50
        result["daily_change"] = 2.15
        result["entry_price"] = 42.00
    elif ticker == "SOXS":
        result["current_price"] = 4.20
        result["daily_change"] = -1.5
    
    # Debug print
    print(f"DEBUG: Checking {ticker}")
    
    try:
        # 1. Load Persisted State
        all_states = get_global_config("triple_filter_states", {})
        state = all_states.get(ticker, {
            "final_met": False, "signal_time": None,
            "step1_done_time": None,
            "step2_done_time": None, "step2_done_price": None,
            "step3_done_time": None, "step3_done_pct": None
        })

        # 2. Get Price & Data
        kis_data = kis_client.get_price(ticker)
        kis_price = kis_data['price'] if kis_data else None

        df30 = None
        if isinstance(data_30m, dict): df30 = data_30m.get(ticker)
        elif hasattr(data_30m, 'columns') and ticker in data_30m.columns: df30 = data_30m[ticker]
        elif hasattr(data_30m, 'columns'): df30 = data_30m # Support Single DF input
        
        df5 = None
        if isinstance(data_5m, dict): df5 = data_5m.get(ticker)
        elif hasattr(data_5m, 'columns') and ticker in data_5m.columns: df5 = data_5m[ticker]
        elif hasattr(data_5m, 'columns'): df5 = data_5m # Support Single DF input

        # Check for missing OR stale data (휴장일 대응)
        data_is_stale = False
        if df30 is not None and not df30.empty:
            try:
                latest_candle_time = df30.index[-1]
                if latest_candle_time.tzinfo is None:
                    latest_candle_time = latest_candle_time.replace(tzinfo=timezone.utc)
                time_since_last_candle = datetime.now(timezone.utc) - latest_candle_time
                # If last candle is older than 12 hours, consider it stale
                if time_since_last_candle.total_seconds() > 172800:  # 48 hours (Include Weekend)
                    data_is_stale = True
            except:
                pass
        
        if df30 is None or df30.empty or df5 is None or df5.empty or data_is_stale:
            # Even if stale, update price from DF if available (Better than fallback)
            if df30 is not None and not df30.empty:
                 result["current_price"] = float(df30['Close'].iloc[-1])
                 
            # Preserve state even if data fetch fails OR is stale (Holiday or Rate Limit)
            if state.get("final_met"):
                result["final"] = True
                result["step1"] = True if state.get("step1_done_time") else False
                result["step2"] = True if state.get("step2_done_time") else False
                result["step3"] = True if state.get("step3_done_time") else False
                result["signal_time"] = state.get("signal_time")
                result["step2_color"] = state.get("step2_color")
                result["step3_color"] = state.get("step3_color")
                
                # Restore Details
                if state.get("step1_done_time"): result["step_details"]["step1"] = f"진입: {state['step1_done_time']}"
                if state.get("step2_done_time"): result["step_details"]["step2"] = f"돌파: {state['step2_done_price']}$"
                if state.get("step3_done_time"): result["step_details"]["step3"] = f"진입: {state['step3_done_time']}"
            return result

        # Force Numeric and Sync KIS
        try:
            df30 = df30.copy()
            df5 = df5.copy()
            df30['Close'] = pd.to_numeric(df30['Close'], errors='coerce').dropna()
            df5['Close'] = pd.to_numeric(df5['Close'], errors='coerce').dropna()
            if kis_price:
                df30.iloc[-1, df30.columns.get_loc('Close')] = kis_price
                df5.iloc[-1, df5.columns.get_loc('Close')] = kis_price
                df5.iloc[-1, df5.columns.get_loc('Close')] = kis_price
        except Exception as e:
            print(f"TRIPLE FILTER ERROR ({ticker}): {e}")
            return result

        current_price = float(df30['Close'].iloc[-1])
        kst = pytz.timezone('Asia/Seoul')
        us_et = pytz.timezone('America/New_York')
        
        # Try to get Chart Time (Signal Time) instead of Server Time
        try:
            # Prefer 5m candle time for precision, else 30m
            if df5 is not None and not df5.empty:
                chart_time = df5.index[-1]
            elif df30 is not None and not df30.empty:
                chart_time = df30.index[-1]
            else:
                chart_time = datetime.now(timezone.utc)
            
            # Ensure it's timezone aware (usually UTC from yfinance)
            if chart_time.tzinfo is None:
                chart_time = chart_time.replace(tzinfo=timezone.utc)
            
            now_utc = chart_time
        except:
             now_utc = datetime.now(timezone.utc)

        # User requested: yyyy.MM.dd HH:mm (Corrected format with dots)
        us_time_formatted = now_utc.astimezone(us_et).strftime("%Y.%m.%d %H:%M")
        kr_time_formatted = now_utc.astimezone(kst).strftime("%Y.%m.%d %H:%M")
        dual_time_str = f"{us_time_formatted} (US) / {kr_time_formatted} (KR)"
        
        # For internal step tracking, use KST full string
        now_time_str = kr_time_formatted

    # --- CALCULATIONS (Updated V2.4 Guidelines) ---
        # Filter 1: 30m Trend (SMA 10 > 30)
        sma10_30 = float(df30['Close'].rolling(window=10).mean().iloc[-1])
        sma30_30 = float(df30['Close'].rolling(window=30).mean().iloc[-1])
        filter1_met = bool(sma10_30 > sma30_30)

        # Filter 2: Daily Change (전일종가 대비 ±2%)
        # Get previous day close (1d data)
        try:
            # Step 2: 30m Trend & Momentum
            # Check Daily Context first (Optional)
            data_1d = None
            if data_1d is None:
                from analysis import _DATA_CACHE
                data_1d = _DATA_CACHE.get("1d")
            
            prev_close = None
            if data_1d is not None:
                if isinstance(data_1d, dict) and ticker in data_1d:
                    df_1d = data_1d[ticker]
                elif hasattr(data_1d, 'columns') and ticker in data_1d.columns:
                    df_1d = data_1d[ticker]
                elif hasattr(data_1d, 'columns'):
                    df_1d = data_1d # Single DF support
                else:
                    df_1d = None
                    
                if df_1d is not None and not df_1d.empty:
                    # Determine Prev Close (Handle Today's candle if present)
                    last_date = df_1d.index[-1]
                    if last_date.date() == datetime.now().date():
                         if len(df_1d) >= 2: prev_close = float(df_1d['Close'].iloc[-2])
                    else:
                         prev_close = float(df_1d['Close'].iloc[-1])
            
            # Apply 2% Breakout Rule (User Priority)
            is_breakout = False
            target_v = 0
            
            if prev_close and prev_close > 0:
                target_v = prev_close * 1.02
                if current_price >= target_v:
                    is_breakout = True
                    state["step2_color"] = "red" # Strong Bullish
            
            if is_breakout and not state.get("step2_done_time"):
                 state["step2_done_time"] = now_utc
                 state["step2_done_price"] = current_price
            
            # If can't get prev close, use yesterday's last 30m candle
            if prev_close is None or pd.isna(prev_close):
                # Fallback: Use close from 24 hours ago in 30m data
                if len(df30) >= 48:  # 24h = 48 x 30min
                    prev_close = float(df30['Close'].iloc[-48])
                else:
                    # Last fallback: use 20-period box high for compatibility
                    recent_20 = df30['High'].tail(21).iloc[:-1]
                    if len(recent_20) < 20: recent_20 = df30['High'].tail(20)
                    prev_close = float(recent_20.max()) / 1.02  # Reverse calculation
            
            # Calculate change percentage
            change_pct = ((current_price - prev_close) / prev_close) * 100
            
            # SOXL: Need +2% or more (Bull)
            # SOXS: Need -2% or less (Bear)
            is_bear_ticker = ticker == "SOXS"
            
            if is_bear_ticker:
                filter2_met = bool(change_pct <= -2.0)  # 2% 이상 하락
                target_v = round(prev_close * 0.98, 2)  # 목표: 전일종가의 -2%
            else:
                filter2_met = bool(change_pct >= 2.0)   # 2% 이상 상승
                target_v = round(prev_close * 1.02, 2)  # 목표: 전일종가의 +2%
            
            result["target"] = target_v
            result["daily_change"] = round(change_pct, 2)  # Store for Frontend
            
        except Exception as e:
            print(f"Filter 2 Calculation Error ({ticker}): {e}")
            # Fallback to old box logic if error
            recent_20 = df30['High'].tail(20)
            box_high_val = float(recent_20.max())
            target_v = round(box_high_val * 1.02, 2)
            result["target"] = target_v
            filter2_met = bool(current_price >= target_v)

        # Filter 3: Timing (5m SMA 10 > 30)
        sma10_5 = float(df5['Close'].rolling(window=10).mean().iloc[-1])
        sma30_5 = float(df5['Close'].rolling(window=30).mean().iloc[-1])
        filter3_met = bool(sma10_5 > sma30_5)

        # --- LOGIC & PERSISTENCE ---
        
        # 1. Check for Reset (30m Trend Break) -> Immediate Exit & Reset
        if not filter1_met:
            # If we were in Final Met state OR Step1 was previously met
            if state.get("final_met") or state.get("step1_done_time"):
                
                # Check if we need to send a SELL signal (Only if we were properly 'IN')
                # If we were in Final Met, this is a Critical Exit
                if state.get("final_met"):
                    result["step1_color"] = "red"
                    result["is_sell_signal"] = True
                    
                    # Reset State Immediately to "Waiting"
                    # User asked to "Change to Red... and Record... and Reset". 
                    # Providing "Red" for this single frame allows the UI to pulse red once, then next fetch it will be grey.
                    
                    state = {
                        "final_met": False, "signal_time": None,
                        "step1_done_time": None, "step2_done_time": None,
                        "step3_done_time": None, "step2_done_price": None,
                        "reset_start_time": None
                    }
                    
                    # Send Exit Signal immediately (rate-limited)
                    try:
                        from db import save_signal, get_connection
                        with get_connection() as conn:
                            with conn.cursor() as cursor:
                                cursor.execute("SELECT id FROM signal_history WHERE ticker=%s AND created_at >= NOW() - INTERVAL 10 MINUTE LIMIT 1", (ticker,))
                                if not cursor.fetchone(): 
                                    save_signal({
                                        'ticker': ticker, 'name': f"Exit Signal ({ticker})",
                                        'signal_type': "SELL (MASTER)", 
                                        'position': f"30분봉 데드크로스 발생: 전량 매도 및 초기화\n시간: {dual_time_str}",
                                        'current_price': current_price, 'signal_time_raw': now_utc,
                                        'is_sent': True, 'score': -100, 'interpretation': "추세 이탈 매도"
                                    })
                    except Exception as e:
                        print(f"Master Signal Exit Save Error: {e}")
                
                else:
                    # Just Step 1 broke without being Final Met
                    # Silent Reset
                    state = {
                        "final_met": False, "signal_time": None,
                        "step1_done_time": None, "step2_done_time": None,
                        "step3_done_time": None, "step2_done_price": None
                    }
                    
                result["step1"] = False
            
            else:
                 # Already waiting, explicitly ensure NO color
                 result["step1_color"] = None
                 pass
        else:
            # Filter 1 (30m Trend) Met
            result["step1"] = True
            if not state.get("step1_done_time"):
                state["step1_done_time"] = now_time_str
            
            # Filter 2 (Box) Check - Sticky if previously met, or live check
            if filter2_met or state.get("step2_done_time"):
                result["step2"] = True
                if not state.get("step2_done_time"):
                    state["step2_done_time"] = now_time_str
                    state["step2_done_price"] = current_price
            else:
                result["step2"] = False 

            # Filter 3 (5m) Check - Live
            result["step3"] = filter3_met
            if filter3_met and result["step2"]: 
                 if not state.get("step3_done_time"):
                     state["step3_done_time"] = now_time_str

            # FINAL ENTRY SIGNAL
            if result["step1"] and result["step2"] and result["step3"]:
                if not state.get("final_met"):
                    state["final_met"] = True
                    state["signal_time"] = dual_time_str 
                    
                    try:
                        from db import save_signal, get_connection
                        with get_connection() as conn:
                            with conn.cursor() as cursor:
                                # Check recent BUY to avoid duplicates
                                cursor.execute("SELECT id FROM signal_history WHERE ticker=%s AND signal_type='BUY (MASTER)' AND created_at >= NOW() - INTERVAL 30 MINUTE LIMIT 1", (ticker,))
                                if not cursor.fetchone(): 
                                    save_signal({
                                        'ticker': ticker, 'name': f"Master Signal ({ticker})",
                                        'signal_type': "BUY (MASTER)", 
                                        'position': f"진입조건완성: 1.30분추세 2.박스돌파 3.5분타이밍\n시간: {dual_time_str}\n가격: ${current_price}",
                                        'current_price': current_price, 'signal_time_raw': now_utc,
                                        'is_sent': True, 'score': 100, 'interpretation': "마스터 트리플 필터 진입"
                                    })
                    except Exception as e:
                        print(f"Master Signal Save Error: {e}")

        # --- POST-ENTRY WARNINGS (Only if final_met is True) ---
        if state.get("final_met"):
            result["final"] = True
            result["signal_time"] = state.get("signal_time", dual_time_str)
            
            # Warning 1: 5m Dead Cross (filter3_met is False) -> Yellow
            if not filter3_met:
                result["step3_color"] = "yellow"
                state["step3_color"] = "yellow"
                result["step3"] = False # Visually not met (Warning)
                # Send SMS/History
                try:
                    from db import save_signal, get_connection
                    with get_connection() as conn:
                        with conn.cursor() as cursor:
                            # Use WARNING (5M) type
                            cursor.execute("SELECT id FROM signal_history WHERE ticker=%s AND signal_type='WARNING (5M)' AND created_at >= NOW() - INTERVAL 30 MINUTE LIMIT 1", (ticker,))
                            if not cursor.fetchone():
                                save_signal({
                                    'ticker': ticker, 'name': f"Warning ({ticker})",
                                    'signal_type': "WARNING (5M)", 
                                    'position': f"5분봉 데드크로스: 긴급 익절(50%) 권장\n현재가: ${current_price}\n시간: {dual_time_str}",
                                    'current_price': current_price, 'signal_time_raw': now_utc,
                                    'is_sent': True, 'score': -50, 'interpretation': "단기 조정 경고"
                                })
                except Exception as e:
                    print(f"Master Signal 5M Warning Save Error: {e}")
            else:
                state["step3_color"] = None

            # Warning 2: Price dropped below entry price -> Orange
            entry_price = state.get("step2_done_price")
            if entry_price and current_price < entry_price:
                result["step2_color"] = "orange"
                state["step2_color"] = "orange"
                try:
                    from db import save_signal, get_connection
                    with get_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT id FROM signal_history WHERE ticker=%s AND signal_type='WARNING (BOX)' AND created_at >= NOW() - INTERVAL 30 MINUTE LIMIT 1", (ticker,))
                            if not cursor.fetchone():
                                price_drop_pct = ((current_price - entry_price) / entry_price) * 100
                                save_signal({
                                    'ticker': ticker, 'name': f"Warning ({ticker})",
                                    'signal_type': "WARNING (BOX)", 
                                    'position': f"진입가 하회: 강도 약화 주의\n진입: ${entry_price:.2f}, 현재: ${current_price:.2f} ({price_drop_pct:+.1f}%)\n시간: {dual_time_str}",
                                    'current_price': current_price, 'signal_time_raw': now_utc,
                                    'is_sent': True, 'score': -30, 'interpretation': "모멘텀 약화 경고"
                                })
                except Exception as e:
                    print(f"Master Signal Box Warning Save Error: {e}")
            else:
                state["step2_color"] = None

        # --- PREPARE DETAILED LOGS ---
        if state.get("step1_done_time"): 
            result["step_details"]["step1"] = f"진입: {state['step1_done_time']}"
        else:
             result["step_details"]["step1"] = f"대기 중 (SMA10: {sma10_30:.2f} / 30: {sma30_30:.2f})"
             
        if state.get("step2_done_time"): 
            result["step_details"]["step2"] = f"돌파: {state['step2_done_price']}$"
        else:
            diff_pct = ((current_price / target_v) - 1) * 100
            result["step_details"]["step2"] = f"대기 중 (목표: ${target_v}, 현재: {diff_pct:.1f}%)"
            
        if state.get("step3_done_time"): 
            result["step_details"]["step3"] = f"진입: {state['step3_done_time']}"
        else:
            result["step_details"]["step3"] = f"대기 중 (5분 추세 확인 필요)"

        # Save & Clean
        all_states[ticker] = state
        set_global_config("triple_filter_states", all_states)

        # JSON Safe
        result["step1"] = bool(result["step1"])
        result["step2"] = bool(result["step2"])
        result["step3"] = bool(result["step3"])
        result["final"] = bool(result["final"])
        result["target"] = float(result["target"])
        result["is_sell_signal"] = bool(result.get("is_sell_signal", False))
        
        # Add entry price and current price for Frontend display
        result["entry_price"] = float(state.get("step2_done_price") or 0)
        result["current_price"] = float(current_price)

        print(f"DEBUG: {ticker} current_price={result.get('current_price')}, daily_change={result.get('daily_change')}")

    except Exception as e:
        print(f"Triple Filter Error ({ticker}): {e}")
        import traceback
        traceback.print_exc()
    
    return result

def determine_market_regime_v2(daily_data, data_30m, data_5m=None):
    """
    Cheongan V2.3 Master Signal Logic (Control Tower)
    """
    if data_5m is None:
        data_5m = _DATA_CACHE.get("5m")

    soxl_res = check_triple_filter("SOXL", data_30m, data_5m)
    soxs_res = check_triple_filter("SOXS", data_30m, data_5m)

    regime = "Sideways"
    reason = "시장 관망 (조건 탐색 중)"
    comment = "SOXL(상승) 또는 SOXS(하락)의 3가지 조건이 모두 충족되어야 방향성이 확정됩니다."
    
    # Calculate Stages
    soxl_count = sum([soxl_res["step1"], soxl_res["step2"], soxl_res["step3"]])
    soxs_count = sum([soxs_res["step1"], soxs_res["step2"], soxs_res["step3"]])
    
    current_strategy = "마스터 신호를 대기하며 현금 비중을 유지합니다. 조건이 완성되는 방향으로 즉각 진입을 준비하세요."
    risk_plan = "현재는 중립 구간입니다. 상승 또는 하락 1단계 진입 시 해당 방향으로 정찰병(5~10%) 투입을 고려하세요."

    # Priority: 1. Final Signal, 2. High Condition Count, 3. Recency (if possible, but count is usually enough)
    if soxs_res["final"]:
        regime = "Bear"
        reason = "🚩 SOXS 진입 조건 완성 (매수)"
        comment = "하락 추세가 확정되었습니다. 공포 심리가 확산되는 구간입니다."
        current_strategy = "SOXS 적극 매수. 레버리지(SOXL, UPRO) 전량 매도. TMF, AAAU 피난처 포트폴리오 구축."
        risk_plan = "하락 3단계 확정. 방어적 포트폴리오 전환 및 인버스 비중 극대화."
        
        # Check Warnings
        if soxs_res.get("step3_color") == "yellow":
            risk_plan = "⚠️ 경고: SOXS 5분봉 데드크로스 발생! 긴급 익절(50%) 및 리스크 관리 필요."
        elif soxs_res.get("step2_color") == "orange":
            risk_plan = "⚠️ 경고: SOXS 박스권 하향 이탈. 매수 강도 약화 주의."

    elif soxl_res["final"]:
        regime = "Bull"
        reason = "🚩 SOXL 진입 조건 완성 (매수)"
        comment = "반도체 상승 에너지가 폭발했습니다. 시장 전체가 강력한 상승 추세로 진입했습니다."
        current_strategy = "SOXL, UPRO, IONQ 적극 매수 및 보유. TSLA, GOOGL 추가 매수 전략 유효. 방어 자산 전량 매도."
        risk_plan = "상승 3단계 확정. 공격적 포트폴리오 운용. 손절 라인 평단 대비 -5% 설정."
        
        # Check Warnings
        if soxl_res.get("step3_color") == "yellow":
            risk_plan = "⚠️ 경고: SOXL 5분봉 데드크로스 발생! 긴급 익절(50%) 및 리스크 관리 필요."
        elif soxl_res.get("step2_color") == "orange":
            risk_plan = "⚠️ 경고: SOXL 박스권 하향 이탈. 매수 강도 약화 주의."

    elif soxs_count > soxl_count:
        regime = f"Bear (Stage {soxs_count})"
        reason = f"⚠️ 하락 {soxs_count}단계 진행 중"
        if soxs_count == 1:
            risk_plan = "하락 1단계: 30분봉 추세 이탈 감지. 수익 실현 및 비중 축소 권장."
        else:
            risk_plan = "하락 2단계: 하락 압력 강화. 인버스(SOXS) 정찰병 진입 및 현금 확보."
    elif soxl_count > soxs_count:
        regime = f"Bull (Stage {soxl_count})"
        reason = f"🔍 상승 {soxl_count}단계 진행 중"
        if soxl_count == 1:
            risk_plan = "상승 1단계: 30분봉 추세 전환 확인. 관망 또는 소량 분할 매수 시작."
        else:
            risk_plan = "상승 2단계: 강한 돌파 확인. 5분봉 골든크로스(3단계) 발생 시 즉시 추가 매수."
    elif soxs_count == soxl_count and soxs_count > 0:
        # Both have progress, check which is more significant (e.g., price change)
        reason = "🌓 혼조세 (방향성 탐색 중)"
        comment = "상승과 하락 조건이 동시에 감지되고 있습니다. 확실한 돌파가 나오기까지 관망이 유리합니다."

    # UPRO status (Requirement #4) - for Journal Header
    upro_change = 0.0
    upro_label = "보합장"
    try:
        upro_df = daily_data.get("UPRO") if isinstance(daily_data, dict) else daily_data["UPRO"]
        if upro_df is not None and not upro_df.empty:
            upro_change = ((upro_df['Close'].iloc[-1] - upro_df['Close'].iloc[-2]) / upro_df['Close'].iloc[-2]) * 100
            if upro_change > 1.5: upro_label = "상승장"
            elif upro_change < -1.5: upro_label = "하락장"
    except: pass

    details = {
        "version": "2.4.0",
        "regime": regime,
        "reason": reason,
        "comment": comment,
        "current_strategy": current_strategy,
        "risk_plan": risk_plan,
        "upro_status": {"label": upro_label, "change_pct": round(upro_change, 2)},
        "soxl": soxl_res,
        "soxs": soxs_res,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        from db import update_market_status
        update_market_status(regime, details)
    except: pass

    return {"regime": regime, "details": details}
    


if __name__ == "__main__":
    # Test run
    print(run_analysis())
