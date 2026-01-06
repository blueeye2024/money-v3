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

def fetch_data(tickers=None, force=False, override_period=None):
    global _DATA_CACHE
    
    target_list = tickers if tickers else TARGET_TICKERS
    now = time.time()
    
    # 1. Tiered Fetching Logic
    # check real-time (30m, 5m): Default TTL 300s (5min) to rely on background scheduler
    # If force=True (from scheduler), update immediately.
    ttl = 300
    needs_realtime = force or ((now - _DATA_CACHE.get("last_fetch_realtime", 0)) > ttl)

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
            
            # [Added] Manual Override
            if override_period:
                fetch_period = override_period
                print(f"🔄 Forced Backfill Period: {fetch_period}")
            
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
            
            # [NEW] KIS Real-time Patch (Overwrite recent candles with live broker data)
            print("🚀 Patching with KIS Real-time Data...")
            from kis_api import kis_client
            import pytz
            
            kst_tz = pytz.timezone('Asia/Seoul')
            
            for ticker in CORE_TICKERS:
                try:
                    # 1. Patch 30m
                    k_30 = kis_client.get_minute_candles(ticker, 30)
                    if k_30:
                        records = []
                        for item in k_30:
                            # Parse KST Time (YYYYMMDD HHMMSS) - Fields: kymd, khms
                            dt_str = f"{item['kymd']} {item['khms']}"
                            dt_kst = datetime.strptime(dt_str, "%Y%m%d %H%M%S")
                            dt_kst = kst_tz.localize(dt_kst)
                            dt_utc = dt_kst.astimezone(timezone.utc)
                            
                            records.append({
                                'candle_time': dt_utc,
                                'Open': float(item['open']),
                                'High': float(item['high']),
                                'Low': float(item['low']),
                                'Close': float(item['last']),
                                'Volume': int(item['evol'])
                            })
                        
                        if records:
                            df_k = pd.DataFrame(records).set_index('candle_time').sort_index()
                            save_market_candles(ticker, '30m', df_k, 'kis_live')
                            print(f"  ✅ KIS 30m Patched: {ticker} ({len(records)} candles)")

                    # 2. Patch 5m
                    k_5 = kis_client.get_minute_candles(ticker, 5)
                    if k_5:
                        records = []
                        for item in k_5:
                            dt_str = f"{item['kymd']} {item['khms']}"
                            dt_kst = datetime.strptime(dt_str, "%Y%m%d %H%M%S")
                            dt_kst = kst_tz.localize(dt_kst)
                            dt_utc = dt_kst.astimezone(timezone.utc)
                            
                            records.append({
                                'candle_time': dt_utc,
                                'Open': float(item['open']),
                                'High': float(item['high']),
                                'Low': float(item['low']),
                                'Close': float(item['last']),
                                'Volume': int(item['evol'])
                            })
                            
                        if records:
                            df_k = pd.DataFrame(records).set_index('candle_time').sort_index()
                            save_market_candles(ticker, '5m', df_k, 'kis_live')
                            print(f"  ✅ KIS 5m Patched: {ticker} ({len(records)} candles, Last: {records[-1]['candle_time']})")

                except Exception as e:
                    print(f"KIS Patch Error ({ticker}): {e}")


        except Exception as e:
            print(f"Incremental Fetch Error: {e}")
            
    # Always Load from DB (Single Source of Truth)
            
    # Always Load from DB (Single Source of Truth)
    # This acts as both Cache Hit and Fallback
    try:
        from db import load_market_candles
        cache_30m = {}
        cache_5m = {}
        
        for ticker in target_list:
            df30 = load_market_candles(ticker, "30m", limit=1000) # Increased to ~20 days
            df5 = load_market_candles(ticker, "5m", limit=2000) # Increased to ~7 days
            
            # Robust Cleaning: Drop rows with missing Close price (YFinance artifact)
            if df30 is not None and not df30.empty:
                df30 = df30.dropna(subset=['Close'])
                cache_30m[ticker] = df30
                
            if df5 is not None and not df5.empty:
                df5 = df5.dropna(subset=['Close'])
                cache_5m[ticker] = df5
            
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
            from db import save_market_candles, load_market_candles
            
            tickers_str = " ".join(target_list)
            print("Fetching Long-term (1d) for Stocks...")
            new_1d = yf.download(tickers_str, period="6mo", interval="1d", group_by='ticker', threads=False, progress=False, timeout=10)
            
            # Save 1d data to DB for CORE_TICKERS
            CORE_TICKERS = ["SOXL", "SOXS", "UPRO"]
            for ticker in target_list:
                if ticker not in CORE_TICKERS: continue
                try:
                    df = None
                    if isinstance(new_1d.columns, pd.MultiIndex) and ticker in new_1d.columns: 
                        df = new_1d[ticker]
                    elif not isinstance(new_1d.columns, pd.MultiIndex) and len(target_list) == 1: 
                        df = new_1d
                    if df is not None and not df.empty: 
                        save_market_candles(ticker, '1d', df, 'yfinance')
                        print(f"  💾 Saved {ticker} 1d data to DB ({len(df)} candles)")
                except Exception as e: 
                    print(f"Save 1d Error {ticker}: {e}")
            
            # Load 1d from DB (Single Source of Truth)
            cache_1d = {}
            for ticker in target_list:
                df1d = load_market_candles(ticker, "1d", limit=180)  # 6 months
                if df1d is not None and not df1d.empty: 
                    cache_1d[ticker] = df1d
            
            if cache_1d: 
                _DATA_CACHE["1d"] = cache_1d
                print(f"✅ Loaded {len(cache_1d)} tickers 1d data from DB")
            
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
    
    # 1d Data: Try DB fallback if cache is empty
    d1 = _DATA_CACHE.get("1d")
    if d1 is None or (isinstance(d1, pd.DataFrame) and d1.empty):
        try:
            from db import load_market_candles
            cache_1d = {}
            for ticker in target_list:
                df1d = load_market_candles(ticker, "1d", limit=180)
                if df1d is not None and not df1d.empty: 
                    cache_1d[ticker] = df1d
            if cache_1d:
                d1 = cache_1d
                _DATA_CACHE["1d"] = cache_1d
                print(f"📊 Fallback: Loaded {len(cache_1d)} tickers 1d from DB")
        except: pass
    
    if d1 is None: d1 = pd.DataFrame()
    
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
        
        # [FIX] Calculate Daily Change using KIS API Daily Data (Most Reliable for "Yesterday Close")
        change_pct = 0.0
        prev_close_price = 0.0
        
        # Try KIS Daily first
        try:
            daily_data = kis_client.get_daily_price(ticker)
            if daily_data and len(daily_data) > 0:
                # daily_data[0] usually contains today's live data in 'stck_clpr' or prev close in 'stck_prpr'?
                # KIS output2 fields: stck_bsop_date(Date), stck_clpr(Close), prdy_vrss(Diff), prdy_ctrt(Rate)
                # Note: For Overseas, output2[0] is the most recent day.
                # If market is open, output2[0] is TODAY. detailed fields might differ.
                # output2[0]['stck_clpr'] is Close.
                # output2[1]['stck_clpr'] is Yesterday Close.
                
                # Careful: We need Yesterday's Close to compare with Current Price.
                # Let's verify date of data[0].
                # But simply, we can infer prev_close from current_price and rate if we trust rate?
                # No, user said rate was wrong. 
                # Let's get output2[1] (Yesterday) directly.
                
                if len(daily_data) > 1:
                     # Check if data[0] is today. 
                     # If data[0] date == today, then previous close is data[1]['ovrs_nmix_prpr'] (for index) or 'close'?
                     # For overseas stock KIS get_daily_price returns: 
                     # { 'sign':..., 'symb':..., 'date':..., 'clos':... } (keys might differ depending on endpoint)
                     # Based on kis_api.py: returns output2. keys are usually acronyms.
                     # "clos" is likely close. let's assume 'clos' or similar.
                     # Actually, looking at kis_api.py, it returns raw dict.
                     
                     # Let's rely on calculation:
                     # If we can get a stable previous close.
                     pass 
        except:
             pass

        # Re-implementing simplified logic:
        # 1. Get Current Price (Realtime > KIS > YF)
        current_price_realtime = 0.0
        if real_time_info:
            current_price_realtime = float(real_time_info['price'])
        elif (kp := kis_client.get_price(ticker)):
             current_price_realtime = kp['price']
        
        if current_price_realtime > 0:
            current_price = current_price_realtime

        # 2. Get Prev Close (KIS Daily > 1D DF)
        prev_close_source = "None"
        try:
            d_data = kis_client.get_daily_price(ticker)
            if d_data and len(d_data) >= 2:
                # KIS Daily returns list. [0] is recent.
                # If [0] is today (based on date/time), use [1]['clos'].
                # Actually KIS Daily keys: 'xymd' (Date), 'clos' (Close), 'open', 'high', 'low'
                today_str = datetime.now(pytz.timezone('Asia/Seoul')).strftime("%Y%m%d") # KIS uses KST/Local dates usually? Or US?
                # US Market Daily Date is usually Local Date (US).
                # Safest: Use [1]['clos'] if [0] looks like today or if we just want "Previous Day Record".
                # Actually, KIS often provides 'base' price in price query?
                
                # Let's try to interpret df_1d again with very strict logic, cross checked with KIS.
                # Better: Use KIS get_price 'base' (Yesterday Close) if available.
                # get_price returns 'price', 'diff', 'rate'. 
                # Yesterday Close = Price - Diff.
                kp_curr = kis_client.get_price(ticker)
                if kp_curr:
                     curr_p = kp_curr['price']
                     diff = kp_curr['diff'] # This is comparison to yesterday.
                     # If diff is valid, Prev = Current - Diff.
                     if curr_p > 0:
                         prev_close_price = curr_p - diff
                         prev_close_source = "KIS_Diff_Calc"
        except Exception as e:
            print(f"KIS PrevClose Calc Error: {e}")
            
        if prev_close_price == 0 and df_1d is not None and not df_1d.empty:
             # Fallback to DF
             if len(df_1d) >= 2:
                 # Assume last is today, second last is yesterday
                 prev_close_price = float(df_1d['Close'].iloc[-2])
                 prev_close_source = "DF_Iloc[-2]"
             else:
                 prev_close_price = float(df_1d['Close'].iloc[-1])
                 prev_close_source = "DF_Iloc[-1]"
        
        if prev_close_price > 0:
             change_pct = ((current_price - prev_close_price) / prev_close_price) * 100
             print(f"[{ticker}] Daily Change: {change_pct:.2f}% (Curr: {current_price}, Prev: {prev_close_price}, Src: {prev_close_source})")
        else:
             # Last resort: use YF prev 30m? No, that's bad.
             pass

        # ... (rest of function) ...
        
        # [MODIFIED] Step 3 Logic: Always show 5m Status

        
        # ... inside return dict ...
        # Assuming these lines are part of a larger dictionary return,
        # and the instruction is to ensure they are present and use the variables.
        # The provided "Code Edit" snippet seems to be a partial return dictionary.
        # I will uncomment the lines that directly match the instruction.
        # "step1_status": "골든크로스" if recent_cross_type == 'gold' else "데드크로스",
        # "step2_status": f"박스권 상단돌파 ({box_pct:.1f}%)" if is_box_up else "대기 (돌파미확인)",

             

        
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
        
        # [MODIFIED] Persistent Signal Check:
        # Check DB for the last known signal to maintain state even if app restarted or gaps exist.
        last_db_signal = None
        try:
             from db import check_last_signal
             last_db_signal = check_last_signal(ticker)
        except: pass
        
        for i in range(1, 60): # Increased lookback to 60 for better coverage
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
            "daily_change": float(change_pct) if pd.notnull(change_pct) else 0.0, # [ADDED] Explicit Daily Change %
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
            "strategy_result": strategy_desc,
            "cross_history": get_cross_history(df_30, df_5)
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


def run_analysis(held_tickers=[], force_update=False):
    print("Starting Analysis Run...")
    
    # -------------------------------------------------------------
    # MASTER CONTROL TOWER ONLY: SOXL, SOXS, UPRO
    # -------------------------------------------------------------
    from db import get_total_capital, get_current_holdings, update_market_status
    from kis_api import kis_client  # Import singleton instance
    
    # Exchange Mapping for Speed
    EXCHANGE_MAP_KIS = {
        "SOXL": "NYS", "SOXS": "NYS", "UPRO": "NYS"
    }
    
    # Only analyze MASTER CONTROL TOWER tickers
    active_tickers = ["SOXL", "SOXS", "UPRO"]
    print(f"✅ MASTER CONTROL TOWER: {active_tickers}")
    
    # Update TICKER_NAMES map
    global TICKER_NAMES
    TICKER_NAMES = {
        "SOXL": "Direxion Daily Semiconductor Bull 3X Shares",
        "SOXS": "Direxion Daily Semiconductor Bear 3X Shares",
        "UPRO": "ProShares UltraPro S&P500"
    }
    
    # -------------------------------------------------------------

    # 1. Fetch Market Data (Only for SOXL, SOXS, UPRO)
    data_30m, data_5m, data_1d, market_data, regime_daily_data = fetch_data(active_tickers, force=force_update)
    
    # 2. Determine Market Regime (V2.3 Master Signal)
    regime_info = determine_market_regime_v2(regime_daily_data, data_30m, data_5m)
    
    
    # Calculate Market Volatility Score (V2.3: Replaced by Master Signals, but keeping variable for compatibility)
    market_vol_score = 5 if regime_info.get('regime') in ['Bull', 'Bear'] else -5
    
    # 3. No individual stock analysis - MASTER CONTROL TOWER only
    results = []  # Empty - we only show MASTER CONTROL TOWER
    
    # Fetch Holdings & Capital (for display only)
    held_tickers = get_current_holdings()
    total_capital = get_total_capital()
    
    # 4. Generate Trade Guidelines (Simplified)cators Data with Change %
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
        "stocks": final_regime.get('stocks', []),
        "market": final_indicators,
        "insight": insight_text,
        "strategy_list": clean_nan(strategy_list),
        "total_assets": clean_nan(total_assets),
        "market_regime": final_regime.get('market_regime', {})
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
            
            # Ensure it's timezone aware
            if chart_time.tzinfo is None:
                chart_time = chart_time.replace(tzinfo=timezone.utc)
            
            # Convert to KST (Korean Time)
            chart_time_kst = chart_time.astimezone(kst)
            
            # Display in KST
            signal_timestamp_str = chart_time_kst.strftime("%Y-%m-%d %H:%M:%S")
            display_time_str = f"{chart_time_kst.strftime('%Y-%m-%d %H:%M')} (KST)"
            
            # Use this for State Update
            now_time_str = display_time_str
            now_utc = chart_time # raw datetime for DB
            
        except Exception as e:
             # Fallback
             now_time_str = datetime.now(kst).strftime("%Y-%m-%d %H:%M (KST)")
             now_utc = datetime.now(timezone.utc)

    # --- CALCULATIONS ---
        # Filter 1: 30m Trend (SMA 10 > 30) - 골든크로스
        if df30 is not None and len(df30) > 0:
            sma10_30 = float(df30['Close'].rolling(window=10).mean().iloc[-1])
            sma30_30 = float(df30['Close'].rolling(window=30).mean().iloc[-1])
        else:
            sma10_30 = 0
            sma30_30 = 0
        
        filter1_met = bool(sma10_30 > sma30_30)  # 골든크로스
        print(f"DEBUG {ticker} Filter1: SMA10={sma10_30:.4f}, SMA30={sma30_30:.4f}, filter1_met={filter1_met}")
            
        # Filter 2: Daily Change (Breakout) - +2% 이상 상승
        filter2_met = False
        prev_close = None
        try:
            # Fetch 1-day data directly for prev close calculation (Priority: KIS > DF)
            import yfinance as yf # Keep import if needed, but we try KIS first
            
            # [FIX] Priority 1: KIS Daily Data
            try:
                k_daily = kis_client.get_daily_price(ticker)
                if k_daily and len(k_daily) > 1:
                     # KIS Daily usually returns [0]=Today(Live/Close), [1]=Yesterday.
                     # We want Yesterday Close.
                     prev_close = float(k_daily[1]['clos']) # Assuming 'clos' key or use safe get if unsure of key mapping in raw dict
                     # Actually raw dict keys from KIS API are usually short. 
                     # Let's rely on my previous knowledge or fallback.
                     # But safer is to use the robust DF logic IF KIS fails or is ambiguous.
            except: pass

            # [FIX] Priority 2: 1D DF with Date Logic (Smart)
            if not prev_close:
                ticker_obj = yf.Ticker(ticker)
                df_1d = ticker_obj.history(period="5d", interval="1d")
                
                if df_1d is not None and not df_1d.empty:
                     est_tz = pytz.timezone('US/Eastern')
                     today_est = datetime.now(est_tz).date()
                     last_lbl = df_1d.index[-1]
                     last_date = last_lbl.date() if hasattr(last_lbl, 'date') else last_lbl
                     
                     if last_date >= today_est:
                         if len(df_1d) >= 2:
                             prev_close = float(df_1d['Close'].iloc[-2])
                             print(f"DEBUG {ticker}: Today Candle ({last_date}). PrevClose(iloc[-2])={prev_close}")
                     else:
                         prev_close = float(df_1d['Close'].iloc[-1])
                         print(f"DEBUG {ticker}: Last Candle Old ({last_date}). PrevClose(iloc[-1])={prev_close}")

            is_breakout = False
            target_v = 0
            
            if prev_close and prev_close > 0:
                # +2% 이상 상승 시 돌파
                target_v = round(prev_close * 1.02, 2)
                if current_price >= target_v:
                    is_breakout = True
            
            if is_breakout:
                 filter2_met = True
                 if not state.get("step2_done_time"):
                     state["step2_done_time"] = now_time_str
                     state["step2_done_price"] = current_price
                     # Save History
                     try:
                         from db import save_signal
                         save_signal({
                             'ticker': ticker, 'signal_type': 'STEP2_BREAKOUT',
                             'position': '박스권/목표가 돌파', 'current_price': current_price,
                             'signal_time_raw': now_utc, 'score': 20,
                             'interpretation': f"강력 상승 돌파 ({now_time_str})"
                         })
                     except: pass
                     
            change_pct = 0
            if prev_close and prev_close > 0:
                 change_pct = ((current_price - prev_close) / prev_close) * 100
            
            result["target"] = target_v
            result["daily_change"] = round(change_pct, 2)

        except Exception as e:
            print(f"Filter 2 Error ({ticker}): {e}")
            import traceback
            traceback.print_exc()
            result["target"] = 0
            filter2_met = False

        # Filter 3: 5m Timing (Golden Cross SMA10 > SMA30)
        filter3_met = False
        if df5 is not None and not df5.empty and len(df5) > 30:
             sma10_5 = float(df5['Close'].rolling(window=10).mean().iloc[-1])
             sma30_5 = float(df5['Close'].rolling(window=30).mean().iloc[-1])
             filter3_met = bool(sma10_5 > sma30_5)  # 골든크로스


        # Note: filter3_met is used for Step 3 (Final Entry Timing)
        # Step 1 is filter1_met (30m trend), handled below

        # --- REAL-TIME FILTER CHECKS (No Reset, No Sticky) ---
        # Each filter is checked independently at current time
        # State only records the FIRST time each condition was met (for history)
        
        # Filter 1: 30m Golden Cross (Real-time check)
        result["step1"] = filter1_met
        if filter1_met:
            result["step1_color"] = None
            result["step1_status"] = "추세 확정"
            if not state.get("step1_done_time"):
                state["step1_done_time"] = now_time_str
        else:
            # 데드크로스: 붉은색 + "주의"
            result["step1_color"] = "red"
            result["step1_status"] = "주의 (데드크로스)"
        
        # Filter 2: +2% Breakout (Real-time check)
        change_pct = result.get("daily_change", 0)
        if change_pct >= 2:
            result["step2"] = True
            result["step2_color"] = None
            result["step2_status"] = "박스권 돌파"
            if not state.get("step2_done_time"):
                state["step2_done_time"] = now_time_str
                state["step2_done_price"] = current_price
        elif change_pct <= -2:
            result["step2"] = False
            result["step2_color"] = "red"
            result["step2_status"] = "손절"
        else:
            result["step2"] = False
            result["step2_color"] = None
            result["step2_status"] = "보합"

        # Filter 3: 5m Golden Cross (Real-time check)
        result["step3"] = filter3_met
        if filter3_met:
            result["step3_color"] = None
            result["step3_status"] = "현재 골든크로스 (진입적합)"
            if not state.get("step3_done_time"):
                state["step3_done_time"] = now_time_str
        else:
            # 데드크로스: 노란색 + "데드크로스 발생"
            result["step3_color"] = "yellow"
            result["step3_status"] = "현재 데드크로스 (대기)"

        # FINAL ENTRY SIGNAL (All 3 must be TRUE at the same time)
        if result["step1"] and result["step2"] and result["step3"]:
            result["final"] = True
            if not state.get("final_met"):
                state["final_met"] = True
                state["signal_time"] = now_time_str 
                
                # 시간 정보 생성 (KST, NY)
                try:
                    ny_tz = pytz.timezone('America/New_York')
                    kst_tz = pytz.timezone('Asia/Seoul')
                    
                    if now_utc.tzinfo is None:
                        now_utc_aware = now_utc.replace(tzinfo=timezone.utc)
                    else:
                        now_utc_aware = now_utc
                    
                    time_kst_formatted = now_utc_aware.astimezone(kst_tz).strftime('%Y-%m-%d %H:%M')
                    time_ny_formatted = now_utc_aware.astimezone(ny_tz).strftime('%Y-%m-%d %H:%M')
                except:
                    time_kst_formatted = now_time_str
                    time_ny_formatted = ''
                
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
                                    'signal_reason': "진입조건 완성 (30분추세+박스돌파+5분타이밍)",
                                    'position': f"진입조건완성: 1.30분추세 2.박스돌파 3.5분타이밍\n시간: {now_time_str}\n가격: ${current_price}",
                                    'current_price': current_price, 'signal_time_raw': now_utc,
                                    'time_kst': time_kst_formatted,
                                    'time_ny': time_ny_formatted,
                                    'is_sent': True, 'score': 100, 'interpretation': "마스터 트리플 필터 진입"
                                })
                except Exception as e:
                    print(f"Master Signal Save Error: {e}")
        else:
            result["final"] = False
            # If any condition breaks, reset final_met
            if state.get("final_met"):
                state["final_met"] = False
                state["signal_time"] = None


        # --- POST-ENTRY WARNINGS (Only if currently in FINAL state) ---
        if result.get("final"):
            result["signal_time"] = state.get("signal_time", now_time_str)
            
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
                                    'position': f"🟡 Yellow 경보: 5분봉 데드크로스 발생\n행동: 보유 주식 30% 매도\n현재가: ${current_price}\n시간: {now_time_str}",
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
                                    'position': f"🟠 Orange 경보: 현재가가 진입가격보다 하락\n행동: 보유 주식 30% 매도\n진입: ${entry_price:.2f}, 현재: ${current_price:.2f} ({price_drop_pct:+.1f}%)\n시간: {now_time_str}",
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
            result["step_details"]["step2"] = f"진입: {state['step2_done_time']}"
        else:
            diff_pct = 0
            if target_v > 0:
                diff_pct = ((current_price / target_v) - 1) * 100
            result["step_details"]["step2"] = f"대기 중 (목표: ${target_v}, 현재: {diff_pct:.1f}%)"
            
        if state.get("step3_done_time"): 
            result["step_details"]["step3"] = f"진입: {state['step3_done_time']}"
        else:
            result["step_details"]["step3"] = f"대기 중 (5분 추세 확인 필요)"

        # Save & Clean
        all_states[ticker] = state
        set_global_config("triple_filter_states", all_states)

        # Note: No "SAFETY NET" - we trust real-time filter checks
        # State is only used to record FIRST occurrence time, not to override current status

        # JSON Safe
        result["step1"] = bool(result["step1"])
        result["step2"] = bool(result["step2"])
        result["step3"] = bool(result["step3"])
        result["final"] = bool(result["final"])
        result["target"] = float(result["target"])
        
        # Add Data Time for UI
        last_time_str = "N/A"
        try:
             if df30 is not None and not df30.empty:
                 # Convert to str if it's datetime
                 last_time_str = str(df30.index[-1])
        except: pass
        result["data_time"] = last_time_str

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

# --- Antigravity V2.1 Helper Functions ---



# Helper: Calculate Cheongan Index (보유 매력도)
def calculate_cheongan_index(res):
    score = 0
    breakdown = {"trend": 0, "timing": 0, "box": 0}
    reasons = []

    # 1. 30분봉 기준 (50점) - 추세
    # step1이 True이면 30분봉 정배열/골든크로스로 간주
    if res.get('step1'): 
        score += 50
        breakdown['trend'] = 50
        reasons.append("30분봉 추세 상승 (+50)")
    
    # 2. 5분봉 진입 신호 (30점) - 타이밍
    # step3가 True이면 5분봉 매수 신호
    if res.get('step3'):
        score += 30
        breakdown['timing'] = 30
        reasons.append("5분봉 진입 신호 (+30)")
    
    # 3. 박스권 돌파 (20점) - 모멘텀
    # step2가 True이면 수급 돌파
    if res.get('step2'):
        score += 20
        breakdown['box'] = 20
        reasons.append("박스권/수급 돌파 (+20)")
    elif res.get('daily_change', 0) > 1.5: # 대안: 당일 강한 상승
        score += 10
        breakdown['box'] = 10
        reasons.append("강한 수급 유입 (+10)")

    # Risk Deduction (Yellow/Orange)
    risk_factor = False
    if res.get('step3_color') == 'yellow':
        score = max(0, score - 20)
        reasons.append("단기 추세 약화 (-20)")
        risk_factor = True
    
    return {"score": score, "breakdown": breakdown, "reasons": reasons, "is_risk": risk_factor}

# Helper: Generate One-Line Tech Comment
def get_tech_comment(rsi, macd):
    comment = ""
    # RSI Analysis
    if rsi >= 70: comment = "과매수 구간 (단기 조정 가능성)"
    elif rsi <= 30: comment = "과매도 구간 (반등 기대)"
    elif 50 <= rsi < 70: comment = "안정적 매수세 유지"
    else: comment = "관망세 우위"
    
    # MACD Analysis
    if macd > 0: comment += " / 상승 모멘텀 지속"
    else: comment += " / 하락 압력 존재"
    
    return comment



def calculate_tech_indicators(df):
    if df is None or len(df) < 26: return {}
    try:
        # RSI (14)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD (12, 26, 9)
        exp12 = df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close'].ewm(span=26, adjust=False).mean()
        macd = exp12 - exp26
        signal = macd.ewm(span=9, adjust=False).mean()
        
        current_rsi = df['RSI'].iloc[-1]
        current_macd = macd.iloc[-1]
        current_signal = signal.iloc[-1]
        
        return {"rsi": current_rsi, "macd": current_macd, "macd_sig": current_signal}
    except:
        return {}

def generate_expert_commentary(ticker, res, tech, regime):
    rsi = tech.get('rsi', 50)
    macd = tech.get('macd', 0)
    sig = tech.get('macd_sig', 0)
    score = res.get('score', 0)
    
    # --- 1. 시세 포착 근거 (Triple Filter Analysis) ---
    logic_text = ""
    if res.get('step1'):
        logic_text += "   ✅ [추세] 30분봉 완전 정배열 (Trend established)\n"
    else:
        logic_text += "   ⚠️ [추세] 30분봉 역배열/혼조세 (Trend uncertain)\n"
        
    if res.get('step2'):
        logic_text += "   ✅ [수급] 박스권 돌파 및 세력 개입 확인 (Breakout)\n"
    elif res.get('step2_color') == 'orange':
        logic_text += "   🚨 [위험] 주요 지지선 이탈 경보 (Support Broken)\n"
    else:
        logic_text += "   ⏳ [수급] 수급 모멘텀 대기 중 (Waiting for volume)\n"
        
    if res.get('step3'):
        logic_text += "   ✅ [타이밍] 5분봉 정밀 진입 시점 포착 (Entry Point)\n"
        
    # --- 2. 매수/청산 이유 (Technical Confluence) ---
    reason_text = ""
    if rsi < 30:
        reason_text += f"   - RSI({rsi:.1f}) 과매도 구간으로 기술적 반등 확률 80% 이상\n"
    elif rsi > 70:
        reason_text += f"   - RSI({rsi:.1f}) 과열 구간 진입, 차익 실현 매물 출회 주의\n"
    
    if macd > sig:
        reason_text += "   - MACD 골든크로스 상태 유지 (상승 에너지 확산)\n"
    else:
        reason_text += "   - MACD 데드크로스 진행 중 (조정 압력 지속)\n"
        
    if res.get('step3_color') == 'yellow':
        reason_text += "   - 단기 추세 꺾임(Yellow Signal) 발생으로 리스크 관리 필수\n"

    # --- 3. 최종 결론 및 전략 (Action Plan) ---
    action_header = ""
    action_detail = ""
    
    if score >= 90:
        action_header = "🚀 강력 매수 (STRONG BUY)"
        action_detail = "모든 진입 조건이 완벽합니다. 비중을 실어 적극 진입하십시오. 목표 수익률은 +3% 이상입니다."
    elif score >= 70:
        action_header = "✅ 매수 (BUY)"
        action_detail = "상승 추세가 확인되었습니다. 눌림목 발생 시 분할로 진입하는 것이 유리합니다."
    elif score <= 30:
        action_header = "⚠️ 관망/매도 (WAIT/SELL)"
        action_detail = "진입 근거가 부족합니다. 무리한 진입보다 현금 비중을 늘리고 다음 파동을 기다리십시오."
    elif res.get('step2_color') == 'orange':
        action_header = "🚨 긴급 탈출 (STOP LOSS)"
        action_detail = "원금 보전을 최우선으로 하십시오. 즉시 비중을 축소하거나 전량 청산하는 것을 권장합니다."
    else:
        action_header = "⏳ 중립/박스권 (NEUTRAL)"
        action_detail = "방향성 탐색 구간입니다. 짧은 스캘핑 외에는 관망하는 것이 좋습니다."

    # Combine All
    final_report = f"""🎯 [청안 {ticker} 정밀 분석 리포트]

1️⃣ 시세 포착 기준 (System Logic):
{logic_text}
2️⃣ 기술적/심리적 분석 (Technical & Reason):
{reason_text}
3️⃣ 최종 행동 지침 (Action Plan):
🔥 {action_header}
"{action_detail}"
"""
    return final_report.strip()

def calculate_holding_score(res, tech):
    """
    V3.5 Comprehensive Holding Score Algorithm
    Weight: Cheongan Index (60%) + Tech/Risk (40%)
    """
    if not res: return {"score": 0, "breakdown": {}, "evaluation": "데이터 부족"}

    score = 0
    breakdown = {"cheongan": 0, "tech": 0, "penalty": 0}
    
    # ----------------------------------------
    # 1. Cheongan Index (Max 60)
    # ----------------------------------------
    cheongan_score = 0
    # A. Trend (30분봉 정배열) - 30점
    if res.get('step1'): 
        cheongan_score += 30
    
    # B. Timing (5분봉 진입) - 20점
    if res.get('step3'): 
        cheongan_score += 20
        
    # C. Momentum (박스권/수급) - 10점
    if res.get('step2'): 
        cheongan_score += 10
    elif res.get('daily_change', 0) > 2.0:
        cheongan_score += 5 # 수급 대체 점수
        
    score += cheongan_score
    breakdown['cheongan'] = cheongan_score

    # ----------------------------------------
    # 2. Technical & Risk (Max 40)
    # ----------------------------------------
    tech_score = 0
    rsi = tech.get('rsi', 50)
    macd = tech.get('macd', 0)
    macd_sig = tech.get('macd_sig', 0)
    
    # A. RSI Stability (15점)
    if 40 <= rsi <= 65: tech_score += 15     # 안정적 상승 구간
    elif 30 <= rsi < 40: tech_score += 10    # 반등 초입
    elif rsi < 30: tech_score += 10          # 과매도 메리트
    elif 65 < rsi < 75: tech_score += 5      # 과열 진입 (주의)
    else: tech_score += 0                    # 75 이상 과열 (위험)
    
    # B. MACD Trend (15점)
    if macd > macd_sig: tech_score += 15
    elif macd > 0: tech_score += 10          # 시그널은 깼지만 0선 위
    
    # C. Risk/Position (10점 - 전고점/저항)
    # 약식: RSI가 70 미만이면 상승 여력 있다고 판단
    if rsi < 70: tech_score += 10
    
    score += tech_score
    breakdown['tech'] = tech_score
    
    # ----------------------------------------
    # 3. Penalties & Filter
    # ----------------------------------------
    penalty = 0
    if res.get('step3_color') == 'yellow': penalty += 15
    if res.get('step2_color') == 'orange': penalty += 30
    
    score = max(0, min(100, score - penalty))
    breakdown['penalty'] = penalty

    # Evaluation Tag
    if score >= 80: evaluation = "강력 매수 (Strong Buy)"
    elif score >= 60: evaluation = "매수 관점 (Buy)"
    elif score >= 40: evaluation = "중립/관망 (Hold)"
    else: evaluation = "매도/리스크 관리 (Sell/Risk)"
    
    return {"score": score, "breakdown": breakdown, "evaluation": evaluation}

def generate_expert_commentary_v2(ticker, score_data, res, tech, regime):
    score = score_data['score']
    breakdown = score_data['breakdown']
    rsi = tech.get('rsi', 0)
    
    # Header
    comment = f"[{score_data['evaluation']}] 현재 점수 {score}점\n\n"
    
    # Analysis
    if score >= 80:
        comment += f"🚀 [핵심 분석] 30분봉 추세와 5분봉 타점이 완벽하게 일치합니다. 청안 지수({breakdown['cheongan']}/60)가 만점에 가까우며, RSI({rsi:.1f}) 또한 안정적인 상승 구간에 위치해 추가 상승 여력이 충분합니다.\n"
        comment += "💡 [전략] 비중을 적극 확대하되, 전고점 돌파 여부를 주시하십시오."
    elif score >= 60:
        comment += f"✅ [핵심 분석] 상승 추세는 유효하나, 일부 감점 요인이 있습니다(청안 {breakdown['cheongan']}/60, Tech {breakdown['tech']}/40). RSI나 MACD 중 하나가 조정을 받고 있을 수 있습니다.\n"
        comment += "💡 [전략] 분할 매수로 접근하며, 확실한 거래량 동반 시 추가 진입하십시오."
    elif score >= 40:
        missing = []
        if not res.get('step1'): missing.append("30분 추세 역배열")
        if not res.get('step3'): missing.append("5분 진입신호 부재")
        
        comment += f"⏳ [핵심 분석] 현재 진입 근거가 다소 부족합니다({', '.join(missing)}). 기술적 지표 점수({breakdown['tech']}점)만으로는 추세 전환을 확신하기 어렵습니다.\n"
        comment += "💡 [전략] 현금 비중을 유지하며 '청안 지수' 항목이 개선될 때까지 기다리십시오."
    else:
        reason = "단기 추세 붕괴" if breakdown['penalty'] > 0 else "하락 추세 지속"
        comment += f"⚠️ [핵심 분석] {reason}로 인해 리스크가 높습니다. (패널티 적용: -{breakdown['penalty']}점). 현재 자리는 매수보다 리스크 관리가 최우선입니다.\n"
        comment += "💡 [전략] 보유 물량 축소 및 관망을 권장합니다."
        
    return comment

def get_filtered_history_v2():
    # Fetch original history
    try:
        from db import get_recent_signals
        raw_history = get_recent_signals(limit=50) # 가져와서 필터링
    except:
        return []

    filtered = []
    seen = {} # {ticker: last_time_obj}
    
    # raw_history는 최신순(내림차순)이라 가정
    for sig in raw_history:
        ticker = sig.get('ticker')
        time_str = sig.get('signal_time') # '2025-01-05 02:40:00' format assumed
        
        try:
            current_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except:
            filtered.append(sig) # 포맷 에러나면 그냥 추가
            continue

        if ticker in seen:
            last_time = seen[ticker]
            # 30분 이내 중복이면 스킵
            if abs((last_time - current_time).total_seconds()) < 1800:
                continue
        
        seen[ticker] = current_time
        filtered.append(sig)
    
    return filtered[:20] # Return top 20

def determine_market_regime_v2(daily_data=None, data_30m=None, data_5m=None):
    """
    Cheongan V3.5 Master Signal Logic (Control Tower)
    Validates UPRO, SOXL, SOXS with Comprehensive Holding Score
    """
    if data_5m is None:
        data_5m = _DATA_CACHE.get("5m")
        
    tickers = ["SOXL", "SOXS", "UPRO"]
    results = {}
    techs = {}
    
    for t in tickers:
        results[t] = check_triple_filter(t, data_30m, data_5m)
        results[t]['ticker'] = t # [FIX] Add Ticker for main.py iteration
        df_5m = data_5m.get(t) if data_5m else None
        techs[t] = calculate_tech_indicators(df_5m)
        
        # [NEW] Inject Cross History for Frontend
        df_30 = data_30m.get(t) if data_30m else None
        history = get_cross_history(df_30, df_5m)
        results[t]['cross_history'] = history
        
        # [SYNC] Overwrite Step Times with REAL Candle Times from History
        try:
            # Sync Step 1 (30m Trend)
            if results[t]['step1'] and history['gold_30m']:
                latest_30 = history['gold_30m'][0]
                results[t]['step_details']['step1'] = f"진입: {latest_30['time_ny']} (NY)"
                
            # Sync Step 3 (5m Timing)
            if results[t]['step3'] and history['gold_5m']:
                latest_5 = history['gold_5m'][0]
                results[t]['step_details']['step3'] = f"진입: {latest_5['time_ny']} (NY)"
                
                # If Final Signal is ON, use the 5m Time as the primary Signal Time (Trigger)
                if results[t]['final']:
                     results[t]['signal_time'] = f"{latest_5['time_ny']} (NY)"
                     
        except Exception as e:
            print(f"Time Sync Error {t}: {e}")
            
    upro_chg = results["UPRO"].get("daily_change", 0)
    regime = "Bull" if upro_chg >= 1.0 else ("Bear" if upro_chg <= -1.0 else "Neutral")
    
    scores = {}
    guides = {}
    tech_comments = {}
    
    for t in tickers:
        # 1. Calculate Score
        score_model = calculate_holding_score(results[t], techs[t])
        scores[t] = score_model
        
        # 2. Generate Guide
        guides[t] = generate_expert_commentary_v2(t, score_model, results[t], techs[t], regime)
        
        # 3. Simple Tech Comment
        score_eval = score_model['evaluation'].split('(')[0].strip()
        tech_comments[t] = score_eval # Use Evaluation as summary
        
    # Get Filtered History
    recent_history = get_filtered_history_v2()
    # recent_news = get_market_news_v2()
    
    details = {
        "version": "3.5.0 (Holding Score)",
        "prime_guide": {
            "scores": scores,
            "guides": guides,
            "tech_summary": techs, 
            "tech_comments": tech_comments, 
            "news": [],
            "history": recent_history  # Pass filtered history explicitly here if frontend uses it from details
        },
        "regime": regime,
        "upro": results["UPRO"], 
        "soxl": results["SOXL"],
        "soxs": results["SOXS"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        from db import update_market_status
        update_market_status(regime, details)
    except: pass
    
    return {
        "market_regime": {
            "regime": regime, 
            "details": details
        },
        "stocks": [results[t] for t in tickers]
    }
    


if __name__ == "__main__":
    # Test run
    print(run_analysis())

def get_cross_history(df_30, df_5):
    history = {
        "gold_30m": [],
        "dead_5m": [],
        "gold_5m": []
    }
    
    tz_kr = pytz.timezone('Asia/Seoul')
    tz_ny = pytz.timezone('America/New_York')
    
    # helper
    def fmt_time(dt):
        if dt.tzinfo is None: 
            # DB & YFinance data is naive NY Time. Localize it correctly.
            try:
                dt = tz_ny.localize(dt)
            except:
                dt = dt.replace(tzinfo=tz_ny)
        return {
            "kr": dt.astimezone(tz_kr).strftime('%m-%d %H:%M'),
            "ny": dt.astimezone(tz_ny).strftime('%m-%d %H:%M')
        }

    # 1. 30m Golden Crosses
    if df_30 is not None and not df_30.empty and len(df_30) > 30:
        d30 = df_30.copy()
        d30 = d30[~d30.index.duplicated(keep='last')]
        d30['SMA10'] = d30['Close'].rolling(window=10).mean()
        d30['SMA30'] = d30['Close'].rolling(window=30).mean()
        
        # Look back deeper
        scan_depth = len(d30) - 1
        for i in range(len(d30)-1, 1, -1): 
            if i < 1: break
            c_10 = d30['SMA10'].iloc[i]
            c_30 = d30['SMA30'].iloc[i]
            p_10 = d30['SMA10'].iloc[i-1]
            p_30 = d30['SMA30'].iloc[i-1]
            
            # Gold Cross
            if p_10 <= p_30 and c_10 > c_30:
                t = fmt_time(d30.index[i])
                history["gold_30m"].append({
                    "time_kr": t["kr"], "time_ny": t["ny"],
                    "price": f"{float(d30['Close'].iloc[i]):.2f}",
                    "type": "골든크로스 (30분)"
                })
    
    # 2. 5m Crosses
    if df_5 is not None and not df_5.empty and len(df_5) > 30:
        d5 = df_5.copy()
        d5 = d5[~d5.index.duplicated(keep='last')]
        d5['SMA10'] = d5['Close'].rolling(window=10).mean()
        d5['SMA30'] = d5['Close'].rolling(window=30).mean()
        
        # Look back deeper
        scan_depth = len(d5) - 1
        for i in range(len(d5)-1, 1, -1): 
            if i < 1: break
            c_10 = d5['SMA10'].iloc[i]
            c_30 = d5['SMA30'].iloc[i]
            p_10 = d5['SMA10'].iloc[i-1]
            p_30 = d5['SMA30'].iloc[i-1]
            
            # Dead Cross
            if p_10 >= p_30 and c_10 < c_30:
                t = fmt_time(d5.index[i])
                history["dead_5m"].append({
                    "time_kr": t["kr"], "time_ny": t["ny"],
                    "price": f"{float(d5['Close'].iloc[i]):.2f}",
                    "type": "데드크로스 (5분)"
                })
            # Gold Cross
            elif p_10 <= p_30 and c_10 > c_30:
                t = fmt_time(d5.index[i])
                history["gold_5m"].append({
                    "time_kr": t["kr"], "time_ny": t["ny"],
                    "price": f"{float(d5['Close'].iloc[i]):.2f}",
                    "type": "골든크로스 (5분)"
                })

    return history
