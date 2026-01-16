import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import pytz
import os
import time
import re
from concurrent.futures import ThreadPoolExecutor
from kis_api_v2 import kis_client
from sms import send_sms
from db import (
    load_market_candles, 
    save_market_candles,
    cleanup_old_candles,
    create_trade,
    close_trade,
    check_open_trade,
    get_trade_history,
    log_history,
    get_v2_buy_status,
    save_v2_buy_signal,
    get_v2_sell_status,
    create_v2_sell_record,
    save_v2_sell_signal
)

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
    "SOXL": "BULL TOWER",
    "SOXS": "BEAR TOWER",
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
    "KRW": "KRW=X",
    "VIX": "^VIX",
    "SOX": "^SOX"  # Philadelphia Semiconductor Index (SOXL/SOXS 추종 지수)
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
    return market_start <= now_est <= market_end

def get_detailed_market_status():
    """
    Returns simplified status: 'OPEN', 'PRE', 'POST', 'DAYTIME', 'CLOSED'
    """
    est = pytz.timezone('US/Eastern')
    kst = pytz.timezone('Asia/Seoul')
    now_est = datetime.now(timezone.utc).astimezone(est)
    now_kst = datetime.now(timezone.utc).astimezone(kst)
    
    # Check Weekend (Sat/Sun) in US Time
    # Weekday 5=Sat, 6=Sun
    # CAUTION: 'Daytime' might act on US Friday Night (Sat Morning KST)? No, Daytime is KST Mon-Fri.
    
    is_weekend = now_est.weekday() >= 5
    
    # 1. US Regular: 09:30 - 16:00
    reg_start = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    reg_end = now_est.replace(hour=16, minute=0, second=0, microsecond=0)
    
    # 2. Pre-Market: 04:00 - 09:30
    pre_start = now_est.replace(hour=4, minute=0, second=0, microsecond=0)
    
    # 3. Post-Market: 16:00 - 20:00
    post_end = now_est.replace(hour=20, minute=0, second=0, microsecond=0)
    
    if not is_weekend:
        if reg_start <= now_est <= reg_end:
            return "OPEN" # 정규장
        elif pre_start <= now_est < reg_start:
            return "PRE"  # 프리장
        elif reg_end < now_est <= post_end:
            return "POST" # 애프터장
            
    # 4. KIS Daytime (Blue Ocean): KST 09:00 - 16:00 (approx)
    # Actually Blue Ocean is 10:00 - 17:00 KST usually?
    # KIS API 'daytime' determines it by volume, but time-wise:
    day_start = now_kst.replace(hour=10, minute=0, second=0, microsecond=0)
    day_end = now_kst.replace(hour=17, minute=0, second=0, microsecond=0) # 5PM
    
    # Check KST Weekday (Mon-Fri)
    if now_kst.weekday() < 5:
        if day_start <= now_kst <= day_end:
            return "DAYTIME"

    return "CLOSED"


def refresh_market_indices():
    """
    Fetches market data and updates DB (market_indices table).
    - KIS API: SOXL, SOXS, UPRO (실시간)
    - YFinance: S&P500, NASDAQ, GOLD, KRW, VIX (지수 - KIS 미지원)
    """
    try:
        print("🌍 Refreshing Market Indices to DB (KIS + YFinance Hybrid)...")
        from db import update_market_indices
        from kis_api_v2 import kis_client, get_exchange_code
        
        data_list = []
        
        # 1. KIS API for Stocks (실시간, 지연 없음)
        kis_tickers = {
            "SOXL": "Direxion Semi Bull 3X",
            "SOXS": "Direxion Semi Bear 3X", 
            "UPRO": "ProShares Ultra S&P500 3X"
        }
        
        for ticker, name in kis_tickers.items():
            try:
                exchange = get_exchange_code(ticker)
                result = kis_client.get_price(ticker, exchange)
                
                if result and result.get('price', 0) > 0:
                    price = result['price']
                    rate = result.get('rate', 0.0)  # 변동률
                    
                    data_list.append({
                        'ticker': ticker,
                        'name': name,
                        'price': float(price),
                        'change': float(rate)
                    })
                    print(f"  ✅ KIS: {ticker} = ${price:.2f} ({rate:+.2f}%)")
                else:
                    # KIS 실패 시 YFinance Fallback
                    t = yf.Ticker(ticker)
                    hist = t.history(period="2d")
                    if not hist.empty:
                        val = hist['Close'].iloc[-1]
                        change = 0.0
                        if len(hist) >= 2:
                            prev = hist['Close'].iloc[-2]
                            change = ((val - prev) / prev) * 100
                        data_list.append({
                            'ticker': ticker,
                            'name': name,
                            'price': float(val),
                            'change': float(change)
                        })
                        print(f"  ⚠️ YF Fallback: {ticker} = ${val:.2f}")
            except Exception as e:
                print(f"  ❌ Error {ticker}: {e}")
        
        # 2. YFinance for Indices (KIS 미지원)
        index_symbols = {
            "S&P500": "^GSPC",
            "NASDAQ": "^IXIC",
            "SOX": "^SOX",  # 필라델피아 반도체 지수 (SOXL/SOXS 추종)
            "GOLD": "GC=F",
            "KRW": "KRW=X",
            "VIX": "^VIX"
        }
        
        for name, symbol in index_symbols.items():
            try:
                t = yf.Ticker(symbol)
                hist = t.history(period="5d")
                if not hist.empty:
                    val = hist['Close'].iloc[-1]
                    change = 0.0
                    if len(hist) >= 2:
                        prev = hist['Close'].iloc[-2]
                        change = ((val - prev) / prev) * 100
                    
                    data_list.append({
                        'ticker': name,
                        'name': symbol,
                        'price': float(val),
                        'change': float(change)
                    })
            except Exception as e:
                print(f"  ❌ Index Error {name}: {e}")
        
        if data_list:
            update_market_indices(data_list)
            print(f"✅ Market Indices Updated: {len(data_list)} items (KIS: {len(kis_tickers)}, YF: {len(index_symbols)})")
            return True
    except Exception as e:
        print(f"Refresh Indices Error: {e}")
        import traceback
        traceback.print_exc()
    return False


def update_market_data(tickers=None, override_period=None):
    """
    BACKGROUND TASK ONLY.
    Fetches data from YFinance/KIS, updates DB, and refreshes Memory Cache.
    """
    global _DATA_CACHE
    target_list = tickers if tickers else TARGET_TICKERS
    now = time.time()
    
    # 1. Refresh Market Indices (Spy, Nasdaq, etc)
    refresh_market_indices()
    
    try:
        from db import save_market_candles, cleanup_old_candles
        
        # Decide fetch period
        fetch_period = "5d" 
        if override_period:
            fetch_period = override_period
            print(f"🔄 Forced Backfill Period: {fetch_period}")
        
        tickers_str = " ".join(target_list)
        print(f"Update: Fetching Real-time (30m, 5m) Period={fetch_period}...")
        
        # Temp Cache for this update
        temp_30m = {}
        temp_5m = {}
        temp_1d = {}
        
        # Fetch from yfinance
        new_30m = yf.download(tickers_str, period=fetch_period, interval="30m", prepost=True, group_by='ticker', threads=True, progress=False, timeout=20)
        new_5m = yf.download(tickers_str, period=fetch_period, interval="5m", prepost=True, group_by='ticker', threads=True, progress=False, timeout=20)
        
        # [NEW] Gap Filling with KIS
        # We only stitch candles for ACTIVE tickers (SOXL, SOXS, UPRO)
        # Because we iterate later, we need to stitch before saving or extracting.
        # But yf.download returns a MultiIndex DF if multiple tickers.
        # We process inside the loop below.
        
        # Save to DB
        CORE_TICKERS = ["SOXL", "SOXS", "UPRO"]
        for ticker in target_list:
            if ticker not in CORE_TICKERS: continue
            
            # Save 30m
            try:
                df = None
                if isinstance(new_30m.columns, pd.MultiIndex) and ticker in new_30m.columns: df = new_30m[ticker]
                elif not isinstance(new_30m.columns, pd.MultiIndex) and len(target_list) == 1: df = new_30m
                if df is not None and not df.empty: 
                    # Mem Cache
                    temp_30m[ticker] = df
                    # DB Save (Deprecated No-op but kept for interface)
                    save_market_candles(ticker, '30m', df, 'yfinance')
            except Exception as e: print(f"Save 30m Error {ticker}: {e}")

            # Save 5m
            try:
                df = None
                if isinstance(new_5m.columns, pd.MultiIndex) and ticker in new_5m.columns: df = new_5m[ticker]
                elif not isinstance(new_5m.columns, pd.MultiIndex) and len(target_list) == 1: df = new_5m
                
                # [STITCH KIS CANDLES]
                if df is not None and not df.empty:
                     df = stitch_kis_candles(ticker, df, 5)

                if df is not None and not df.empty: 
                    # Mem Cache
                    temp_5m[ticker] = df
                    # DB Save
                    save_market_candles(ticker, '5m', df, 'yfinance')
            except Exception as e: print(f"Save 5m Error {ticker}: {e}")

        # Update Long-term (Regime Data)
        print("Update: Fetching Daily data for Market Regime...")
        reg_tickers = ["UPRO", "^GSPC", "^IXIC", "SPY"]
        new_regime = yf.download(reg_tickers, period="6mo", interval="1d", group_by='ticker', threads=False, progress=False, timeout=20)
        if not new_regime.empty: 
            _DATA_CACHE["regime"] = new_regime
            # Save 1d data for Regime tickers if needed? Ideally yes but skipping for speed for now.
        
        # Save 1d for Stocks
        print("Update: Fetching Long-term (1d) for Stocks...")
        new_1d = yf.download(tickers_str, period="6mo", interval="1d", group_by='ticker', threads=False, progress=False, timeout=10)
        for ticker in target_list:
            if ticker not in CORE_TICKERS: continue
            try:
                df = None
                if isinstance(new_1d.columns, pd.MultiIndex) and ticker in new_1d.columns: df = new_1d[ticker]
                elif not isinstance(new_1d.columns, pd.MultiIndex) and len(target_list) == 1: df = new_1d
                if df is not None and not df.empty: 
                    temp_1d[ticker] = df
                    save_market_candles(ticker, '1d', df, 'yfinance')
            except: pass

        # Perform KIS Patching logic and DB update (simplified call or inline)
        # For brevity, I will assume we reload from DB after this to get the "Cleanest" data,
        # OR we can inject KIS here. Let's rely on load_from_db to do the final composition
        # to ensure strong consistency.
        
        print("✅ Background Data Update & InMemory Save Complete.")
        
        # DIRECTLY UPDATE MEMORY CACHE (Since DB Load is deprecated)
        if temp_30m: _DATA_CACHE["30m"] = temp_30m
        if temp_5m: _DATA_CACHE["5m"] = temp_5m
        if temp_1d: _DATA_CACHE["1d"] = temp_1d
        _DATA_CACHE["last_fetch_realtime"] = time.time()
        
        # Finally, Load indices (Load from DB logic still has indices)
        load_data_from_db(target_list)
        
    except Exception as e:
        print(f"Background Update Error: {e}")

def load_data_from_db(target_list=None):
    """Reloads _DATA_CACHE from DB (Fast)"""
    global _DATA_CACHE
    if not target_list: target_list = TARGET_TICKERS
    
    try:
        from db import load_market_candles, get_market_indices
        
        # 1. Load Indices
        _DATA_CACHE["market"] = get_market_indices()
        
        
        # [DEPRECATED V5.1.0] Legacy Tables (soxl_candle_data etc) Removed.
        # We now rely on in-memory gap filling using update_market_data().
        # Returning empty cache here triggers update_market_data() in fetch_data.
        
        # 1. Load Indices (Keep this)
        _DATA_CACHE["market"] = get_market_indices()
        
        # 2. Return empty candle cache to force fresh fetch
        # Since we don't persist candles to DB anymore (Snapshot Only strategy),
        # we must always fetch fresh data on startup/analysis.
        return _DATA_CACHE
        
        # KIS Live Patching (Fast, Direct Broker API)
        # We do this on LOAD so the cache always has the latest live price on top of DB history
        try:
            from kis_api_v2 import kis_client
            EXCHANGE_MAP = {"SOXL": "NYS", "SOXS": "NYS", "UPRO": "NYS"}
            for ticker in ["SOXL", "SOXS", "UPRO"]:
                if ticker in cache_30m or ticker in cache_5m:
                    kis = kis_client.get_price(ticker, exchange=EXCHANGE_MAP.get(ticker))
                    if kis and kis['price'] > 0:
                        if ticker in cache_30m: 
                            # Safe update last row
                            # cache_30m[ticker].iloc[-1, cache_30m[ticker].columns.get_loc('Close')] = kis['price'] 
                            # Better: Append or Update intelligently? Just update close for now.
                            idx = cache_30m[ticker].index[-1]
                            cache_30m[ticker].at[idx, 'Close'] = kis['price']
                            
                        if ticker in cache_5m: 
                            idx = cache_5m[ticker].index[-1]
                            cache_5m[ticker].at[idx, 'Close'] = kis['price']
                            
            # [NEW] Gap Filling: Stitch KIS 5m Candles
            print("  🧵 Stitching KIS Candles to fill 15m delay...")
            from kis_api_v2 import kis_client
            for ticker in target_list:
                if ticker not in ["SOXL", "SOXS", "UPRO"]: continue # Only for main tickers
                
                try:
                    # Stitch 30m candles (Interval 30)
                    # stitch_kis_candles(ticker, cache_30m, 30) # Optional, mostly focused on 5m
                    
                    # Stitch 5m candles (Interval 5)
                    if ticker in cache_5m and not cache_5m[ticker].empty:
                        original_len = len(cache_5m[ticker])
                        stitched_df = stitch_kis_candles(ticker, cache_5m[ticker], 5)
                        if stitched_df is not None:
                            cache_5m[ticker] = stitched_df
                            print(f"    - {ticker}: {original_len} -> {len(stitched_df)} rows (Gap Filled)")
                            
                except Exception as e_stitch:
                    print(f"    ❌ Stitching Error {ticker}: {e_stitch}")
                            
        except Exception as e: print(f"KIS Patch Error: {e}")

        # Update Cache
        if cache_30m: _DATA_CACHE["30m"] = cache_30m
        if cache_5m: _DATA_CACHE["5m"] = cache_5m
        if cache_1d: _DATA_CACHE["1d"] = cache_1d
        
        _DATA_CACHE["last_fetch_realtime"] = time.time()
        print(f"✅ Cache Refreshed from DB: {len(cache_30m)} tickers")
        
    except Exception as e:
        print(f"Load from DB Error: {e}")

def fetch_data(tickers=None, force=False, override_period=None):
    """
    READ-ONLY Access to Data.
    If force=True, it triggers a background update (synchronously for now, or assume managed by scheduler).
    Ideally, this just returns _DATA_CACHE.
    """
    global _DATA_CACHE
    
    # If cache is empty, try loading from DB immediately
    # (Since V5.1.0, DB loading is deprecated for candles, so this might remain empty)
    if _DATA_CACHE.get("30m") is None or not _DATA_CACHE.get("30m"):
        load_data_from_db(tickers)
        
    # [FIX] If cache is STILL empty (DB deprecated), we MUST fetch from API immediately.
    # Otherwise analysis will fail with empty DataFrames.
    if _DATA_CACHE.get("30m") is None or not _DATA_CACHE.get("30m"):
        print("⚠️ Cache Empty after DB Load. Forcing API fetch (V5.1.0)...")
        update_market_data(tickers, override_period="5d")

    # If force=True (Scheduler), run the update logic
    if force:
        update_market_data(tickers, override_period)
        
    # Return Cache
    d30 = _DATA_CACHE.get("30m") if _DATA_CACHE.get("30m") is not None else pd.DataFrame()
    d5 = _DATA_CACHE.get("5m") if _DATA_CACHE.get("5m") is not None else pd.DataFrame()
    d1 = _DATA_CACHE.get("1d") if _DATA_CACHE.get("1d") is not None else pd.DataFrame()
    m = _DATA_CACHE.get("market") if _DATA_CACHE.get("market") is not None else {}
    reg = _DATA_CACHE.get("regime") if _DATA_CACHE.get("regime") is not None else pd.DataFrame()
    
    return d30, d5, d1, m, reg

import pandas_ta as ta

def calculate_sma(series, window):
    return ta.sma(series, length=window)

def calculate_ema(series, span):
    return ta.ema(series, length=span)

def calculate_rsi(series, window=14):
    return ta.rsi(series, length=window)

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
                     # Based on kis_api_v2.py: returns output2. keys are usually acronyms.
                     # "clos" is likely close. let's assume 'clos' or similar.
                     # Actually, looking at kis_api_v2.py, it returns raw dict.
                     
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
        # Check DB for th
        # [Restored Logic]
        
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

        # [Ver 3.9] Market Intelligence (Refactored)
        new_metrics = calculate_market_intelligence(df_30)
        
        # 6. Total Score
        final_score = base_score + trend_score + reliability_score + breakout_score + market_score + pnl_impact
        final_score = int(max(0, min(100, final_score)))
        
        score_interpretation = get_score_interpretation(final_score, position)
        
        result = {
            "ticker": ticker,
            "name": stock_name,
            "current_price": float(current_price) if pd.notnull(current_price) else None,
            "daily_change": float(change_pct) if pd.notnull(change_pct) else 0.0,
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
            "score_interpretation": score_interpretation,
            "new_metrics": new_metrics,
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

def generate_trade_guidelines(results, market_data, regime_info, total_capital=10000.0, held_tickers=None, krw_rate=1460.0):
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
    # Calculate Capital Status
    current_holdings_value = 0.0
    
    # Adapter: Handle List of Dicts (Merged DB) or Dict (Legacy)
    iterator = []
    if held_tickers is None:
        held_tickers = {} # Ensure it's a dict if not provided
    if isinstance(held_tickers, list):
         iterator = [(h['ticker'], h) for h in held_tickers]
    elif isinstance(held_tickers, dict):
         iterator = held_tickers.items()

    for ticker, info in iterator:
        curr_price = info.get('avg_price', 0)
        # Find current price in results
        for r in results:
            if r['ticker'] == ticker:
                curr_price = r.get('current_price', 0)
                break
        
        qty = info.get('qty', 0)
        current_holdings_value += (qty * curr_price)
        
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


def run_analysis(holdings=None, force_update=False):
    """
    Main entry point for analysis.
    ...
    """
    global _LATEST_REPORT
    
    start_total = time.time()
    if holdings is None:
        from db import get_current_holdings
        holdings = get_current_holdings()
    print("Starting Analysis Run...")
    
    # -------------------------------------------------------------
    # MASTER CONTROL TOWER ONLY: SOXL, SOXS, UPRO
    # -------------------------------------------------------------
    from db import get_total_capital, update_market_status
    from kis_api_v2 import kis_client  # Import singleton instance
    
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
        "SOXL": "BULL TOWER",
        "SOXS": "BEAR TOWER",
        "UPRO": "ProShares UltraPro S&P500"
    }
    
    # -------------------------------------------------------------

    # 1. Fetch Market Data (Only for SOXL, SOXS, UPRO)
    data_30m, data_5m, data_1d, market_data, regime_daily_data = fetch_data(active_tickers, force=force_update)
    
    # 2. Determine Market Regime (V2.3 Master Signal)
    regime_output = determine_market_regime_v2(regime_daily_data, data_30m, data_5m)
    regime_info = regime_output.get('market_regime', {})
    
    # Calculate Market Volatility Score (V2.3: Replaced by Master Signals, but keeping variable for compatibility)
    market_vol_score = 5 if regime_info.get('regime') in ['Bull', 'Bear'] else -5
    
    # 3. No individual stock analysis - MASTER CONTROL TOWER only
    results = regime_output.get('stocks', [])
    print(f"DEBUG: run_analysis results count: {len(results)}")
    if len(results) > 0:
         print(f"DEBUG: result tickers: {[r.get('ticker') for r in results]}")
    
    # Fetch Holdings & Capital (for display only)
    # holdings is already passed or fetched
    total_capital = get_total_capital()
    
    # 4. Generate Trade Guidelines (Simplified)cators Data with Change %
    indicators = {}
    
    # Convert market_data from list to dict if needed
    # Convert market_data from list to dict if needed
    market_data_dict = {}
    
    if isinstance(market_data, list):
        # market_data is a list of dicts from get_market_indices()
        for item in market_data:
            if isinstance(item, dict) and 'ticker' in item:
                market_data_dict[item['ticker']] = item
                
    elif isinstance(market_data, dict):
        market_data_dict = market_data
        
    # [Fix] Ensure market_data_dict is a dictionary before .items() call
    if not isinstance(market_data_dict, dict):
        print(f"⚠️ market_data_dict is not dict (Type: {type(market_data_dict)}). Resetting to empty.")
        market_data_dict = {}
    
    for name, data in market_data_dict.items():
        try:
            val = 0.0
            change = 0.0
            
            # [DB Mode] Data is dict {'price': ..., 'change': ...}
            if isinstance(data, dict):
                val = data.get('current_price', data.get('price', 0.0))
                change = data.get('change_pct', data.get('change', 0.0))
                
            # [Legacy Mode] Data is DataFrame
            elif isinstance(data, pd.DataFrame) and not data.empty and 'Close' in data.columns:
                val = data['Close'].iloc[-1]
                if len(data) >= 2:
                    prev = data['Close'].iloc[-2]
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
    insight_text, strategy_list, total_assets = generate_trade_guidelines(results, market_data, regime_info, total_cap, holdings)

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
    
    # [NEW] Simple Market Status
    m_status = get_detailed_market_status()
    
    # [NEW] Check duplicates before saving to DB
    # (Since we iterate results, we do this before constructing full_report_dict or after)
    
    # 5. Save Snapshots to DB (Optimization)
    try:
        from db import save_market_snapshot
        for res in final_results:
             # Map result keys to DB columns
             # DB cols: ticker, candle_time, rsi_14, vol_ratio, atr, pivot_r1, macd, macd_sig, 
             # gold_30m, gold_5m, dead_30m, dead_5m, score, evaluation, strategy_comment, v2_state
             
             snapshot_data = {
                 'ticker': res['ticker'],
                 'candle_time': res.get('signal_time_raw') or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 'rsi': res.get('rsi', 0),
                 'vr': res.get('new_metrics', {}).get('vol_ratio', 0), # vol_ratio in new_metrics? check analyze_ticker
                 'atr': res.get('new_metrics', {}).get('atr', 0),
                 'pivot_r1': res.get('new_metrics', {}).get('pivot', {}).get('r1', 0),
                 'macd': res.get('macd', 0),
                 'macd_sig': res.get('macd_sig', 0),
                 'gold_30m': 'Y' if res.get('last_cross_type') == 'gold' else 'N', # simplistic mapping
                 'gold_5m': 'Y' if '매수' in res.get('position', '') else 'N', # simplistic mapping
                 'dead_30m': 'Y' if res.get('last_cross_type') == 'dead' else 'N',
                 'dead_5m': 'Y' if '매도' in res.get('position', '') else 'N',
                 'score': res.get('score', 0),
                 'evaluation': res.get('score_interpretation', ''),
                 'comment': res.get('strategy_result', ''),
                 'v2_state': res.get('position', '')
             }
             save_market_snapshot(snapshot_data)
             
    except Exception as e_snap:
        print(f"Snapshot Save Error: {e_snap}")

    full_report = {
        "summary": "Market Analysis",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "analysis_latency": f"{time.time() - start_total:.2f}s",
        "stocks": final_results,
        "holdings": holdings,
        "market": final_indicators, # [Ver 5.3 FIX] Renamed 'indices' to 'market' for Frontend
        "insight": insight_text,
        "strategy_list": clean_nan(strategy_list),
        "total_assets": clean_nan(total_assets),
        "market_regime": final_regime,
        "market_status": m_status, # "OPEN", "PRE", "POST", "DAYTIME", "CLOSED"
        "is_market_open": (m_status == "OPEN") # Backward compatibility
    }
    
    # [Cache Update]
    _LATEST_REPORT = full_report
    
    return full_report

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




def check_triple_filter(ticker, data_30m, data_5m):
    """
    [Refactored V5.6] Single Source of Truth
    - READ-ONLY from DB (populated by run_v2_signal_analysis)
    - No Calculation of MA/Signals here.
    - No DB Updates here.
    """
    from db import fetch_signal_status_dict, get_global_config
    import datetime
    
    # 1. Initialize Result Dict (Frontend Contract)
    result = {
        "step1": False, "step2": False, "step3": False, "final": False, 
        "step1_color": None, "step2_color": None, "step3_color": None,
        "target": 0, "signal_time": None, "is_sell_signal": False,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "step_details": {
            "step1": "대기 중", "step2": "대기 중", "step3": "대기 중"
        },
        "current_price": 0.0,
        "daily_change": 0.0,
        "entry_price": 0.0,
        "name": TICKER_NAMES.get(ticker, ticker), # [FIX] Add Name for Frontend/Console
        "sounds": [],
        "price_alerts": []
    }

    print(f"DEBUG: Checking {ticker} (Read-Only Mode)")

    try:
        # 2. Fetch Truth from DB
        db_status = fetch_signal_status_dict(ticker)
        buy_db = db_status.get('buy')
        sell_db = db_status.get('sell')
        
        # 3. Get Current Price (for Display only)
        # Try KIS first, then DF
        current_price = 0.0
        daily_change = 0.0
        
        # Try KIS Cache or Live
        from kis_api_v2 import kis_client
        kis_data = kis_client.get_price(ticker)
        if kis_data and kis_data.get('price', 0) > 0:
             current_price = float(kis_data['price'])
             daily_change = float(kis_data.get('rate', 0))
             
             # [Ver 5.7.3] Day High Logic (API vs DB)
             # KIS API 'high' is often 0 for overseas. Use DB (calculated from candles) if available.
             api_high = float(kis_data.get('high', 0))
             db_high = 0.0
             if buy_db and buy_db.get('day_high_price'):
                 db_high = float(buy_db['day_high_price'])
             
             result['day_high'] = max(api_high, db_high)
             if result['day_high'] == 0 and api_high > 0: result['day_high'] = api_high
        
        # Fallback to DF if KIS failed
        if current_price == 0:
             df30 = None
             if isinstance(data_30m, dict): df30 = data_30m.get(ticker)
             elif hasattr(data_30m, 'columns'): df30 = data_30m
             
             if df30 is not None and not df30.empty:
                 current_price = float(df30['Close'].iloc[-1])

        result['current_price'] = current_price
        result['daily_change'] = daily_change

        # 4. Map DB Status to Result
        if buy_db:
            # Step 1
            result['step1'] = (buy_db.get('buy_sig1_yn') == 'Y')
            result['step1_status'] = "진입 타점 (5m Gold)" if result['step1'] else "진입 대기"
            if not result['step1']: result['step1_color'] = "yellow"
            
            # Step 2
            result['step2'] = (buy_db.get('buy_sig2_yn') == 'Y')
            result['step2_status'] = "박스권 돌파" if result['step2'] else "보합/대기"
            
            # Step 3
            result['step3'] = (buy_db.get('buy_sig3_yn') == 'Y')
            result['step3_status'] = "추세 확정 (30m Gold)" if result['step3'] else "추세 미확보"
            if not result['step3']: result['step3_color'] = "yellow"

            # Final
            result['final'] = (buy_db.get('real_buy_yn') == 'Y') or (result['step1'] and result['step2'] and result['step3'])
            
            # Details (Timestamps)
            result['step_details']['step1'] = f"시간: {buy_db.get('buy_sig1_dt') or '-'}"
            result['step_details']['step2'] = f"시간: {buy_db.get('buy_sig2_dt') or '-'}"
            result['step_details']['step3'] = f"시간: {buy_db.get('buy_sig3_dt') or '-'}"
            
            # Target / Entry
            result['entry_price'] = float(buy_db.get('real_buy_price') or buy_db.get('final_buy_price') or 0)
            
            # Manual Overrides Status
            if buy_db.get('is_manual_buy1') == 'Y': result['step1_status'] = "수동 설정 (ON)"
            if buy_db.get('is_manual_buy2') == 'Y': result['step2_status'] = "수동 설정 (ON)"
            if buy_db.get('is_manual_buy3') == 'Y': result['step3_status'] = "수동 설정 (ON)"

        # 5. Map Sell Status (for Alert)
        if sell_db:
            # Check if ANY sell signal is active
            is_sell = False
            if sell_db.get('sell_sig1_yn') == 'Y': is_sell = True
            if sell_db.get('sell_sig2_yn') == 'Y': is_sell = True
            if sell_db.get('sell_sig3_yn') == 'Y': is_sell = True
            
            result['is_sell_signal'] = is_sell
            
        # 6. Keep Market Intelligence (Metrics Display)
        # This is stateless, so safe to calculate for UI
        df30 = None
        if isinstance(data_30m, dict): df30 = data_30m.get(ticker)
        elif hasattr(data_30m, 'columns'): df30 = data_30m
        
        if df30 is not None and not df30.empty:
            result['new_metrics'] = calculate_market_intelligence(df30)

        # 7. Add Data Time for UI (Safe Fallback)
        last_time_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
             if df30 is not None and not df30.empty:
                 last_time_str = df30.index[-1].strftime('%Y-%m-%d %H:%M:%S')
        except: pass
        result["data_time"] = last_time_str

        # 8. Price Alerts (Read-Only Check)
        try:
             from db import get_price_levels, set_price_level_triggered
             levels = get_price_levels(ticker)
             # Logic to just display alerts not triggering them? 
             # Actually, run_v2 triggers them. We just display.
             for lvl in levels:
                 if lvl['is_active'] == 'Y': 
                      # Add to alerts list for frontend display logic
                      pass
        except: pass

    except Exception as e:
        print(f"Refactored Check Error ({ticker}): {e}")
        import traceback
        traceback.print_exc()

    return result


# --- Antigravity V2.1 Helper Functions ---

# --- Helper Functions for Market Intelligence ---
def calculate_market_intelligence(df):
    """
    Calculate advanced metrics: Vol Ratio, ATR, Pivot R1, RSI
    """
    metrics = {}
    try:
        # 1. Vol Ratio (Current Vol / 20-period Avg Vol) with Safety Check
        if 'Volume' in df.columns and len(df) >= 20:
            vol_sma = ta.sma(df['Volume'], length=20)
            cur_vol = df['Volume'].iloc[-1]
            avg_vol = vol_sma.iloc[-1] if vol_sma is not None else 0
            
            if avg_vol > 0:
                metrics['vol_ratio'] = round((cur_vol / avg_vol) * 100, 2) # Percent
            else:
                metrics['vol_ratio'] = 0.0
        else:
            metrics['vol_ratio'] = 0.0

        # 2. ATR (Average True Range, 14 period)
        try:
             atr_series = ta.atr(df['High'], df['Low'], df['Close'], length=14)
             if atr_series is not None:
                 metrics['atr'] = round(atr_series.iloc[-1], 2)
             else:
                 metrics['atr'] = 0.0
        except:
             metrics['atr'] = 0.0
        
        # 3. Pivot R1 (Classic Pivot Points)
        # Pivot = (H + L + C) / 3
        # R1 = 2*P - L
        try:
            high = df['High'].iloc[-1]
            low = df['Low'].iloc[-1]
            close = df['Close'].iloc[-1]
            pivot = (high + low + close) / 3
            r1 = (2 * pivot) - low
            r2 = pivot + (high - low)
            metrics['pivot_r1'] = round(r1, 2)
            metrics['pivot_r2'] = round(r2, 2)
        except:
            metrics['pivot_r1'] = 0.0
            metrics['pivot_r2'] = 0.0

        # 4. RSI (14) - Include it here for easy access
        try:
             rsi_series = ta.rsi(df['Close'], length=14)
             if rsi_series is not None:
                 metrics['rsi'] = round(rsi_series.iloc[-1], 2)
             else:
                 metrics['rsi'] = 50.0
        except:
             metrics['rsi'] = 50.0

    except Exception as e:
        print(f"Market Intelligence Error: {e}")
        return {}
        
    return metrics

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
    if df is None: return {}
    if not hasattr(df, 'columns'): return {} # Not a DataFrame
    if 'Close' not in df.columns: return {}
    if len(df) < 26: return {}
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

def get_evaluation_label(score):
    if score >= 80: return "강력 매수 (Strong Buy)"
    elif score >= 60: return "매수 관점 (Buy)"
    elif score >= 40: return "중립/관망 (Hold)"
    else: return "매도/리스크 관리 (Sell/Risk)"


def calculate_holding_score(res, tech, v2_buy=None, v2_sell=None):
    """
    V4.0 안티그래비티 스코어 시스템 (Antigravity Score System)
    
    [청안 지수] V2 신호 기반 (Max 60점)
    - 1단계만: 20점, 2단계까지: 30점, 3단계 완료: 60점
    
    [안티그래비티 보조지표] 비대칭 가감점 (+40 ~ -80점)
    - RSI: +10 ~ -20
    - MACD: +10 ~ -20
    - Vol Ratio: +10 ~ -20
    - ATR: +10 ~ -20
    
    [총점 범위] -80 ~ +100점
    [매수 기준] 90+: 강력매수, 70+: 매수, 60+: 매수추천, 60미만: 관망
    """
    if not res: return {"score": 0, "breakdown": {}, "evaluation": "데이터 부족"}

    # Initialize Breakdown
    breakdown = {
        "cheongan": 0,    # 청안 지수 (V2 Signals)
        "rsi": 0,         # RSI 점수
        "macd": 0,        # MACD 점수
        "vol": 0,         # Vol Ratio 점수
        "atr": 0,         # ATR 점수
        "total": 0
    }
    
    # ================================================
    # 1. 청안 지수 (V2 Signal Base) - Max 60점
    # ================================================
    cheongan_score = 0
    sig1 = v2_buy and v2_buy.get('buy_sig1_yn') == 'Y'
    sig2 = v2_buy and v2_buy.get('buy_sig2_yn') == 'Y'
    sig3 = v2_buy and v2_buy.get('buy_sig3_yn') == 'Y'
    
    if sig3:
        cheongan_score = 60  # 3단계 완료
    elif sig2:
        cheongan_score = 30  # 2단계까지
    elif sig1:
        cheongan_score = 20  # 1단계만
    
    breakdown['cheongan'] = cheongan_score
    
    # ================================================
    # 2. 안티그래비티 보조지표 (+40 ~ -80점)
    # ================================================
    rsi = tech.get('rsi', 50)
    macd = tech.get('macd', 0)
    macd_sig = tech.get('macd_sig', 0)
    
    new_metrics = res.get('new_metrics', {})
    vol_ratio = new_metrics.get('vol_ratio', 1.0)
    atr = new_metrics.get('atr', 0)
    current_price = res.get('current_price', 0)
    daily_change = res.get('daily_change', 0)
    
    # ---- A. RSI 채점 (+10 ~ -20) ----
    rsi_score = 0
    if 55 < rsi < 65:
        rsi_score = 10   # 상승 추세 안정적 진입
    elif 45 < rsi <= 55:
        rsi_score = 5    # 추세 전환 시도
    elif 30 < rsi <= 45:
        rsi_score = -10  # 하락 추세 지속
    elif rsi <= 30 or rsi >= 75:
        rsi_score = -20  # 과매도/단기 상투 위험
    breakdown['rsi'] = rsi_score
    
    # ---- B. MACD 채점 (+10 ~ -20) ----
    macd_score = 0
    macd_diff = macd - macd_sig if macd_sig else macd
    
    if macd > macd_sig and macd > 0:
        macd_score = 10   # 골든크로스 + 양수 = 강세
    elif macd > macd_sig:
        macd_score = 5    # 골든크로스 (조정 중)
    elif macd < macd_sig and macd >= 0:
        macd_score = -10  # 데드크로스 시작
    elif macd < 0 and macd < macd_sig:
        macd_score = -20  # 강력한 하락 추세
    breakdown['macd'] = macd_score
    
    # ---- C. Vol Ratio 채점 (+10 ~ -20) ----
    # [V4.0.1] 상승 + 고VR + 고RSI 조합 시 경계 신호 추가
    vol_score = 0
    if vol_ratio > 2.0 and daily_change < 0:
        vol_score = -20   # 투매 발생 (최우선 판단)
    elif vol_ratio > 2.0 and daily_change > 0 and rsi > 70:
        vol_score = 0     # 경계: 폭등이지만 과열 위험 (가점 없음)
    elif vol_ratio > 1.5 and daily_change > 0:
        vol_score = 10    # 강력한 매수세 유입
    elif vol_ratio > 1.0:
        vol_score = 5     # 평균 이상 관심
    elif 0.5 < vol_ratio <= 0.8:
        vol_score = -10   # 매수세 실종
    breakdown['vol'] = vol_score
    
    # ---- D. ATR 채점 (+10 ~ -20) ----
    atr_score = 0
    atr_ratio = (atr / current_price) if current_price > 0 else 0
    
    if daily_change > 1 and atr_ratio > 0.02:
        atr_score = 10    # 강한 추세적 돌파
    elif daily_change > 0:
        atr_score = 5     # 완만한 우상향
    elif daily_change < 0 and atr_ratio > 0.02:
        atr_score = -10   # 공포 섞인 하락
    elif daily_change < -3 and atr_ratio > 0.03:
        atr_score = -20   # 패닉셀 구간
    breakdown['atr'] = atr_score
    
    # ================================================
    # 3. 총점 계산
    # ================================================
    indicator_total = breakdown['rsi'] + breakdown['macd'] + breakdown['vol'] + breakdown['atr']
    total_score = breakdown['cheongan'] + indicator_total
    
    # 범위 제한: -80 ~ 100
    total_score = max(-80, min(100, total_score))
    breakdown['total'] = total_score
    
    # ================================================
    # 4. 평가 라벨 (매수 기준)
    # ================================================
    if total_score >= 90:
        evaluation = "🚀 강력 매수 (Strong Buy)"
    elif total_score >= 70:
        evaluation = "✅ 매수 (Buy)"
    elif total_score >= 60:
        evaluation = "💡 매수 추천 (Recommended)"
    else:
        evaluation = "⏳ 관망 (Hold/Watch)"
    
    return {
        "score": total_score,
        "breakdown": breakdown,
        "evaluation": evaluation,
        "new_metrics": new_metrics
    }


def generate_expert_commentary_v2(ticker, score_data, res, tech, regime, v2_buy=None, v2_sell=None):
    score = score_data['score']
    breakdown = score_data['breakdown']
    rsi = tech.get('rsi', 0)
    
    # V2 Status
    is_v2_active = v2_buy and v2_buy.get('final_buy_yn') == 'Y'
    v2_stage = ""
    if v2_buy:
        if v2_buy.get('buy_sig3_yn') == 'Y': v2_stage = "3차 진입완료"
        elif v2_buy.get('buy_sig2_yn') == 'Y': v2_stage = "2차 진입완료"
        elif v2_buy.get('buy_sig1_yn') == 'Y': v2_stage = "1차 진입완료"
        
    # [Ver 3.9] Intelligence Data
    new_metrics = res.get('new_metrics', {})
    vol_ratio = new_metrics.get('vol_ratio', 1.0)
    pivot_r1 = new_metrics.get('pivot_r1', 0)
    current_price = res.get('current_price', 0)
    
    # --- Score Breakdown Header ---
    bd_text = f"[채점표] 추세 +{breakdown.get('trend', 0)} | 지표 "
    if breakdown.get('macd', 0) != 0: bd_text += f"MACD{breakdown['macd']:+d} "
    if breakdown.get('rsi', 0) != 0: bd_text += f"RSI{breakdown['rsi']:+d} "
    if breakdown.get('vol', 0) != 0: bd_text += f"VOL{breakdown['vol']:+d} "
    
    # Penalty display
    if breakdown.get('penalty', 0) != 0: 
        bd_text += f"| 감점 -{breakdown['penalty']}"
    
    comment = f"{bd_text.strip()}\n"

    # Analysis Body
    if score >= 80:
        comment += f"🚀 [Action] 강력 매수/보유 (Strong Buy). "
        if is_v2_active: comment += f"V2 시스템이 {v2_stage} 상태입니다. "
        comment += f"추세와 보조지표가 모두 상승을 가리킵니다.\n"
        comment += "💡 수익을 극대화(Let profits run)하십시오."
        
    elif score >= 60:
        comment += f"✅ [Action] 매수 관점 (Buy). 상승 모멘텀이 유효합니다.\n"
        
        tech_sum = breakdown.get('macd', 0) + breakdown.get('rsi', 0) + breakdown.get('vol', 0)
        if tech_sum > 0: comment += "기술적 지표가 긍정적입니다. "
        comment += f"💡 분할 매수로 접근하십시오."
        if vol_ratio < 0.8: comment += " (단, 거래량 부족 주의)"
        
    elif score >= 40:
        comment += f"⏳ [Action] 관망/중립 (Hold). "
        if breakdown.get('penalty', 0) > 0: comment += f"패널티 요소(-{breakdown['penalty']})가 있어 진입을 보류합니다.\n"
        else: comment += "뚜렷한 상승 신호가 부족합니다.\n"
        comment += "💡 다음 V2 신호를 기다리십시오."
        
    else: # Score < 40
        comment += f"⚠️ [Action] 매도/리스크 관리 (Sell). "
        comment += f"하락 우위 상태입니다.\n"
        comment += "💡 현금 확보 및 포지션 축소를 권장합니다."
        
    # Resistance Check
    if score >= 60 and pivot_r1 > current_price and (pivot_r1 - current_price)/current_price < 0.01:
        comment += f"\n🚨 1차 저항선({pivot_r1:.2f}) 접근 중. 돌파 실패 시 단기 대응 필요."

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
        d30['SMA10'] = ta.sma(d30['Close'], length=10)
        d30['SMA30'] = ta.sma(d30['Close'], length=30)
        
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
        d5['SMA10'] = ta.sma(d5['Close'], length=10)
        d5['SMA30'] = ta.sma(d5['Close'], length=30)
        
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

    # Limit to latest 1 (User Request)
    history["gold_30m"] = history["gold_30m"][:1]
    history["gold_5m"] = history["gold_5m"][:1]
    history["dead_5m"] = history["dead_5m"][:1]

    return history


def process_auto_trading(ticker, result_info, current_price, current_time):
    """
    Process auto trading logic (Simulation)
    - Entry: Final Signal == True AND No Open Trade
    - Exit: 30m Trend (Step1) == Dead Cross AND Open Trade
    """
    try:
        # Check current status
        open_trade = check_open_trade(ticker)
        
        # 1. Entry Logic
        if result_info['final'] and not open_trade:
            # Only enter if signal time is recent (e.g. within 2 hours or same day)
            # For simulation, we trust the 'final' flag which implies conditions are met NOW.
            create_trade(ticker, current_price, current_time)
            print(f"🚀 [AUTO BUY] {ticker} at {current_price}")
            
        # 2. Exit Logic (Trend Reversal)
        elif open_trade:
            # Exit if Step 1 is NOT met (i.e., Dead Cross or not confirmed)
            # result_info['step1'] is True if Golden Cross maintained.
            # If Step1 becomes False -> Trend broken.
            if not result_info['step1']:
                 close_trade(ticker, current_price, current_time)
                 print(f"📉 [AUTO SELL] {ticker} at {current_price}")
                 
    except Exception as e:
        print(f"Auto Trading Error ({ticker}): {e}")

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
        
        # [NEW] Inject Cheongan V2 Status
        if t in ['SOXL', 'SOXS']:
            try:
                # Convert dates/decimals to serializable format if needed, 
                # but run_analysis usually does this at the end or FastAPI handles it via custom encoder?
                # Actually, main.py's get_v2_status uses a helper serialize().
                # We should do similar or rely on results being dicts.
                # DB returns Decimals/Datetimes. JSON response will fail if not handled.
                # check_triple_filter likely handles its own.
                # Let's add them as is, but we might need to handle serialization in main.py or here.
                # Ideally, we convert them here to be safe.
                
                v2_buy = get_v2_buy_status(t)
                v2_sell = get_v2_sell_status(t)
                
                def serialize_v2(obj):
                    if not obj: return None
                    new = dict(obj)
                    for k, v in new.items():
                        if isinstance(v, (datetime, pd.Timestamp)):
                             new[k] = v.strftime('%Y-%m-%d %H:%M:%S')
                        elif hasattr(v, '__float__'): # Decimal
                             new[k] = float(v)
                    return new

                results[t]['v2_buy'] = serialize_v2(v2_buy)
                results[t]['v2_sell'] = serialize_v2(v2_sell)
            except Exception as e:
                print(f"V2 Injection Error {t}: {e}")

        # --- Auto Trading Simulation ---
        try:
            cur_price = results[t]['current_price'] if 'current_price' in results[t] else 0
            # Use signal time or current NY time
            # Ideally use the timestamp of the latest candle
            process_auto_trading(t, results[t], cur_price, datetime.now(timezone.utc))
            
        except Exception as e:
            print(f"Auto trade processing failed for {t}: {e}")
        # -------------------------------
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
    regime = "Bull" if upro_chg >= 1.0 else ("Bear" if upro_chg <= -1.5 else "Neutral")
    
    scores = {}
    guides = {}
    tech_comments = {}
    
    for t in tickers:
        # [V3.8] Retrieve V2 Status (Already fetched in results[t])
        v2_buy_info = None
        v2_sell_info = None
        if t in ['SOXL', 'SOXS']:
             # Access raw DB version via results[t]['v2_buy'] which is a DICT (serialized)
             # But calculate_holding_score might expect dict access.
             v2_buy_info = results[t].get('v2_buy')
             v2_sell_info = results[t].get('v2_sell')
             
        # 1. Calculate Score
        score_model = calculate_holding_score(results[t], techs[t], v2_buy_info, v2_sell_info)
        scores[t] = score_model
        
        # 2. Generate Guide
        guides[t] = generate_expert_commentary_v2(t, score_model, results[t], techs[t], regime, v2_buy_info, v2_sell_info)
        
        # 3. Simple Tech Comment
        score_eval = score_model['evaluation'].split('(')[0].strip()
        tech_comments[t] = score_eval # Use Evaluation as summary
        
        # [NEW] Log Strategy & Indicators to DB (Consolidated)
        try:
             # Snapshot (Dashboard) + History (Backtest)
             from db import save_market_snapshot, log_market_history
             
             new_metrics = results[t].get('new_metrics', {})
             signals = new_metrics.get('signals', {})
             
             # Calculate V2 State
             v2_state = 'WAIT'
             if results[t].get('final'): v2_state = 'FINAL_MET'
             elif results[t].get('step3'): v2_state = 'STEP3_MET'
             elif results[t].get('step2'): v2_state = 'STEP2_MET'
             elif results[t].get('step1'): v2_state = 'STEP1_MET'
             
             log_data = {
                 'ticker': t,
                 'candle_time': results[t].get('data_time'), 
                 'rsi': new_metrics.get('rsi', 0),
                 'vr': new_metrics.get('vol_ratio', 0),
                 'atr': new_metrics.get('atr', 0),
                 'pivot_r1': new_metrics.get('pivot_r1', 0),
                 'macd': techs[t].get('macd', 0) if techs.get(t) else 0,
                 'macd_sig': techs[t].get('macd_sig', 0) if techs.get(t) else 0,
                 'gold_30m': signals.get('gold_30m', 'N') if signals else 'N',
                 'gold_5m': signals.get('gold_5m', 'N') if signals else 'N',
                 'dead_30m': signals.get('dead_30m', 'N') if signals else 'N',
                 'dead_5m': signals.get('dead_5m', 'N') if signals else 'N',
                 'score': score_model.get('score', 0),
                 'evaluation': score_model.get('evaluation', ''),
                 'comment': guides[t],
                 'v2_state': v2_state
             }
             if t in ['SOXL', 'SOXS']: # Only log target tickers
                 save_market_snapshot(log_data) # Update Dashboard immediately
                 log_market_history(log_data)   # Archive for analysis
        except Exception as e:
             print(f"Log Strategy Error {t}: {e}")
        
    # Get Filtered History
    recent_history = get_filtered_history_v2()
    # recent_news = get_market_news_v2()
    
    # [Ver 5.8.2] Dynamic Version String
    version_str = f"Ver 5.8.2 (Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')})"
    
    details = {
        "version": version_str,
        "prime_guide": {
            "scores": scores,
            "guides": guides,
            "tech_summary": techs, 
            "tech_comments": tech_comments, 
            "news": [],
            "history": recent_history,
            "trade_history": get_trade_history(limit=20) # [NEW] Auto Trade Logs
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


# --- Cheongan V2 Signal Analysis ---
def run_v2_signal_analysis():
    print(f"🚀 Backend Starting V5.6 Signal Analysis... ")
    """
    Cheongan V2 3-Step Buy/Sell Logic Implementation
    Run via Scheduler (Every 5 mins)
    """
    global _LAST_ANALYSIS_TIME
    print(f"🔄 V2 Signal Analysis Started...")
    import kis_api_v2
    
    # 1. Target Tickers
    targets = ['SOXL', 'SOXS']

    # [Ver 5.6] Fetch Market Indices Map (for Patching)
    market_map = {}
    try:
        from db import get_market_indices
        indices = get_market_indices()
        for item in indices:
            market_map[item['ticker']] = item
        print(f"✅ Loaded Market Map: {len(market_map)} items")
    except Exception as e:
        print(f"⚠️ Failed to load Market Map: {e}")
    
    # 2. Fetch Data (Force Update for Real-time accuracy)
    try:
        data_30m, data_5m, data_1d, _, _ = fetch_data(targets, force=True)
    except Exception as e:
        print(f"❌ V2 Data Fetch Error: {e}")
        return
        
    if data_30m is None or data_5m is None:
        print("⚠️ V2 Data Fetch returned None (skipping analysis)")
        return
        
    for ticker in targets:
        try:
            # Data Check
            df_5 = data_5m.get(ticker)
            df_30 = data_30m.get(ticker)
            
            if df_5 is None or df_5.empty or df_30 is None or df_30.empty:
                print(f"⚠️ {ticker} Insufficient Data for V2 Analysis")
                continue
                
            # --- Clean Data (Resample to ensure strict 5m/30m intervals) ---
            # To avoid duplicate rows or non-snapped timestamps disrupting MA
            if not isinstance(df_5.index, pd.DatetimeIndex):
                df_5.index = pd.to_datetime(df_5.index)
            if not isinstance(df_30.index, pd.DatetimeIndex):
                df_30.index = pd.to_datetime(df_30.index)
            
            # Resample and take last close (Handle ticks)
            # using '5min' for pandas < 2.2, '5min' is standard alias
            
            def get_agg_dict(columns):
                agg_dict = {'Close': 'last'}
                if 'Open' in columns: agg_dict['Open'] = 'first'
                if 'High' in columns: agg_dict['High'] = 'max'
                if 'Low' in columns: agg_dict['Low'] = 'min'
                if 'Volume' in columns: agg_dict['Volume'] = 'sum'
                return agg_dict

            try:
                df_5 = df_5.resample('5min').agg(get_agg_dict(df_5.columns)).dropna()
                df_30 = df_30.resample('30min').agg(get_agg_dict(df_30.columns)).dropna()
            except Exception as e:
                print(f"⚠️ Resample Failed for {ticker} (Using Raw Data): {e}")
                # Fallback: Use raw data if resampling crashes (e.g. missing columns)
                pass
            
            # --- Indicators Calculation ---
            # 5m
            df_5['ma10'] = df_5['Close'].rolling(window=10).mean()
            df_5['ma30'] = df_5['Close'].rolling(window=30).mean()
            
            # 30m
            try:
                df_30['ma10'] = df_30['Close'].rolling(window=10).mean()
                df_30['ma30'] = df_30['Close'].rolling(window=30).mean()
                # Check High column exists
                if 'High' in df_30.columns:
                    df_30['box_high'] = df_30['High'].rolling(window=20).max().shift(1)
                else:
                    df_30['box_high'] = 0
                
                df_30['vol_ma5'] = df_30['Volume'].rolling(window=5).mean()
                
                # 1D (Prev Close)
                prev_close = 0
                if data_1d is not None and ticker in data_1d:
                    d1 = data_1d[ticker]
                    if not d1.empty:
                        try:
                            # [FIX] Robust Prev Close Logic
                            # If last candle is Today (NY Time), use iloc[-2].
                            # If last candle is Yesterday, use iloc[-1].
                            import pytz
                            
                            ny_date = datetime.now(pytz.timezone('US/Eastern')).date()
                            last_bar_dt = d1.index[-1]
                            last_bar_date = last_bar_dt.date() if hasattr(last_bar_dt, 'date') else last_bar_dt.date()
                            
                            # Check if latest bar is from today (or future)
                            if last_bar_date >= ny_date:
                                if len(d1) >= 2:
                                    prev_close = float(d1['Close'].iloc[-2])
                                else:
                                    prev_close = float(d1['Close'].iloc[-1]) # Fallback (Startup)
                            else:
                                # Latest bar is yesterday (or older)
                                prev_close = float(d1['Close'].iloc[-1])
                                
                        except Exception as e:
                            print(f"PrevClose Error: {e}")
                            if len(d1) >= 2: prev_close = float(d1['Close'].iloc[-2])
                
                # Current Values
                curr_price = float(df_5['Close'].iloc[-1])
                curr_vol_30 = float(df_30['Volume'].iloc[-1])
                curr_vol_ma_30 = float(df_30['vol_ma5'].iloc[-1]) if not pd.isna(df_30['vol_ma5'].iloc[-1]) else 0
                box_high = float(df_30['box_high'].iloc[-1]) if 'box_high' in df_30.columns and not pd.isna(df_30['box_high'].iloc[-1]) else 0
            except Exception as e:
                print(f"Skipping Indicators for {ticker} due to data error: {e}")
                continue
            
            # [Ver 5.6] Patch Price/PrevClose from DB (market_indices) - Source: KIS/YFinance
            # User Request: "market_indices 테이블에서 가져오면 됨"
            patch_data = market_map.get(ticker)
            if patch_data:
                try:
                    p_price = float(patch_data['current_price'])
                    p_change = float(patch_data['change_pct'])
                    
                    if p_price > 0:
                        curr_price = p_price
                        # Calculate Prev Close inversely from Change % and Current Price
                        # Prev = Current / (1 + rate/100)
                        if p_change > -99.9: # Safety check
                            prev_close = curr_price / (1 + (p_change / 100.0))
                            print(f"  🎯 DB Patch {ticker}: Price={curr_price}, Change={p_change}%, Prev={prev_close:.2f}")
                        else:
                            print(f"  ⚠️ DB Patch Suspicious Rate: {p_change}%")
                except Exception as e:
                    print(f"  ⚠️ DB Patch Error {ticker}: {e}")

            # 5m Indicators
            ma10_5 = df_5['ma10'].iloc[-1]
            ma30_5 = df_5['ma30'].iloc[-1]
            prev_ma10_5 = df_5['ma10'].iloc[-2]
            prev_ma30_5 = df_5['ma30'].iloc[-2]
            
            # 30m Indicators
            ma10_30 = df_30['ma10'].iloc[-1]
            ma30_30 = df_30['ma30'].iloc[-1]
            prev_ma10_30 = df_30['ma10'].iloc[-2]
            prev_ma30_30 = df_30['ma30'].iloc[-2]
            
            # --- Logic Checking ---
            
            # [Ver 5.8.3] Independent Signal Processing
            # Each signal checks and updates INDEPENDENTLY
            # Sound duplicate prevention using set
            sounds_to_play = set()
            
            # --- BUY SIDE ---
            buy_record = get_v2_buy_status(ticker)
            
            # Condition checks (calculated once, used multiple times)
            is_5m_gc_cross = (prev_ma10_5 <= prev_ma30_5) and (ma10_5 > ma30_5)
            is_5m_trend_up = (ma10_5 > ma30_5)
            is_30m_gc = (prev_ma10_30 <= prev_ma30_30) and (ma10_30 > ma30_30)
            is_30m_trend_up = (ma10_30 > ma30_30)
            
            # 2% breakout condition
            cond_2pct = (prev_close > 0) and (curr_price > prev_close * 1.02)
            
            # Ensure buy_record exists for signal tracking
            if not buy_record:
                # Create new record on first signal
                if is_5m_trend_up or cond_2pct or is_30m_trend_up:
                    kst_now = datetime.now(timezone.utc).astimezone(pytz.timezone('Asia/Seoul'))
                    manage_id = f"{ticker}_{kst_now.strftime('%Y%m%d')}"
                    from db import create_initial_buy_record
                    try:
                        create_initial_buy_record(ticker, manage_id)
                        buy_record = get_v2_buy_status(ticker)
                        print(f"✨ {ticker} Created new buy record: {manage_id}")
                    except Exception as e:
                        print(f"⚠️ {ticker} Could not create buy record: {e}")
            
            # Check if we are in HOLDING mode (already bought)
            is_holding = buy_record and buy_record.get('final_buy_yn') == 'Y'
            
            # === SIGNAL 1: 5분봉 Golden Cross (INDEPENDENT) ===
            if buy_record and not is_holding:
                manage_id = buy_record.get('manage_id', 'UNKNOWN')
                sig1_manual = buy_record.get('is_manual_buy1') == 'Y'
                
                if is_5m_trend_up:
                    # Condition MET → Turn ON (if not already)
                    if buy_record['buy_sig1_yn'] == 'N':
                        if save_v2_buy_signal(ticker, 'sig1', curr_price):
                            msg_type = "5분봉 GC" if is_5m_gc_cross else "5분봉 상승추세"
                            print(f"🚀 {ticker} Signal 1 ON ({msg_type})")
                            log_history(manage_id, ticker, "1차매수신호", msg_type, curr_price)
                            sounds_to_play.add(('buy1', ticker))
                else:
                    # Condition NOT MET → Turn OFF (if not manual)
                    if buy_record['buy_sig1_yn'] == 'Y' and not sig1_manual:
                        try:
                            from db import manual_update_signal
                            manual_update_signal(ticker, 'buy1', 0, 'N')
                            print(f"📉 {ticker} Signal 1 OFF (5m trend lost)")
                        except: pass
            
            # === SIGNAL 2: +2% 돌파 (INDEPENDENT) ===
            if buy_record and not is_holding:
                sig2_manual = buy_record.get('is_manual_buy2') == 'Y'
                
                # Calculate sig2 condition
                custom_target = buy_record.get('target_box_price')
                if custom_target and float(custom_target) > 0:
                    is_sig2_met = (curr_price >= float(custom_target))
                    sig2_reason = f"지정가도달(${custom_target})"
                else:
                    baseline = float(buy_record.get('buy_sig1_price') or prev_close or 0)
                    if baseline > 0:
                        is_sig2_met = (curr_price >= baseline * 1.02)
                        sig2_reason = f"+2% (기준: ${baseline:.2f})"
                    else:
                        is_sig2_met = cond_2pct
                        sig2_reason = "+2% 전일대비"
                
                if is_sig2_met:
                    if buy_record['buy_sig2_yn'] == 'N':
                        if save_v2_buy_signal(ticker, 'sig2', curr_price):
                            print(f"🚀 {ticker} Signal 2 ON ({sig2_reason})")
                            log_history(manage_id, ticker, "2차매수신호", sig2_reason, curr_price)
                            sounds_to_play.add(('buy2', ticker))
                else:
                    if buy_record['buy_sig2_yn'] == 'Y' and not sig2_manual:
                        try:
                            from db import manual_update_signal
                            manual_update_signal(ticker, 'buy2', 0, 'N')
                            print(f"📉 {ticker} Signal 2 OFF (condition lost)")
                        except: pass
            
            # === SIGNAL 3: 30분봉 Golden Cross (INDEPENDENT) ===
            if buy_record and not is_holding:
                sig3_manual = buy_record.get('is_manual_buy3') == 'Y'
                
                if is_30m_trend_up:
                    if buy_record['buy_sig3_yn'] == 'N':
                        if save_v2_buy_signal(ticker, 'sig3', curr_price):
                            msg_type = "30분봉 GC" if is_30m_gc else "30분봉 상승추세"
                            print(f"🚀 {ticker} Signal 3 ON ({msg_type})")
                            log_history(manage_id, ticker, "3차매수신호", msg_type, curr_price)
                            sounds_to_play.add(('buy3', ticker))
                else:
                    if buy_record['buy_sig3_yn'] == 'Y' and not sig3_manual:
                        try:
                            from db import manual_update_signal
                            manual_update_signal(ticker, 'buy3', 0, 'N')
                            print(f"📉 {ticker} Signal 3 OFF (30m trend lost)")
                        except: pass
            
            # === FINAL BUY SIGNAL CHECK ===
            if buy_record and not is_holding:
                updated_buy = get_v2_buy_status(ticker)
                if updated_buy:
                    all_met = (updated_buy['buy_sig1_yn'] == 'Y' and 
                               updated_buy['buy_sig2_yn'] == 'Y' and 
                               updated_buy['buy_sig3_yn'] == 'Y')
                    
                    if all_met and updated_buy['final_buy_yn'] == 'N':
                        if save_v2_buy_signal(ticker, 'final', curr_price):
                            print(f"🎯 {ticker} FINAL BUY SIGNAL! All conditions met.")
                            log_history(manage_id, ticker, "최종진입완료", "Triple Filter Complete", curr_price)
                            sounds_to_play.add(('final_buy', ticker))
            
            # === SEND SMS (최대 1개만 - 우선순위: final > 3 > 2 > 1) ===
            if sounds_to_play:
                sms_time = get_current_time_str_sms()
                if ('final_buy', ticker) in sounds_to_play:
                    send_sms(ticker, "최종매수(V2)", curr_price, sms_time, "트리플필터완성")
                elif ('buy3', ticker) in sounds_to_play:
                    send_sms(ticker, "3차매수(30분봉)", curr_price, sms_time, "30분봉 추세확정")
                elif ('buy2', ticker) in sounds_to_play:
                    send_sms(ticker, "2차매수(박스권)", curr_price, sms_time, "+2% 돌파")
                elif ('buy1', ticker) in sounds_to_play:
                    send_sms(ticker, "1차매수(5분봉)", curr_price, sms_time, "5분봉 골든크로스")
            # --- SELL SIDE (Position Management) ---
            # [Ver 5.8.3] Independent Signal Processing for SELL
            sell_sounds = set()
            sell_record = get_v2_sell_status(ticker)

            # Create sell record if in HOLDING but no sell record
            if not sell_record and buy_record and buy_record.get('final_buy_yn') == 'Y':
                from db import create_v2_sell_record
                manage_id = buy_record.get('manage_id', 'UNKNOWN')
                entry_price = buy_record.get('final_buy_price') or curr_price
                if create_v2_sell_record(ticker, entry_price):
                    print(f"✨ {ticker} Created sell record (entry: ${entry_price})")
                    sell_record = get_v2_sell_status(ticker)

            # Only process sell signals if in HOLDING mode
            if sell_record and is_holding:
                manage_id = sell_record.get('manage_id', 'UNKNOWN')
                
                # Calculate conditions once
                is_5m_dc = (prev_ma10_5 >= prev_ma30_5) and (ma10_5 < ma30_5)
                is_5m_trend_down = (ma10_5 < ma30_5)
                
                # Day High calculation
                day_high = curr_price
                if df_5 is not None and not df_5.empty:
                    recent_high = df_5['High'].tail(80).max()
                    day_high = max(day_high, float(recent_high))
                
                trailing_stop_price = day_high * 0.985
                is_trailing_stop = (curr_price <= trailing_stop_price)
                
                # Save Day High to DB
                try:
                    from db import get_connection
                    with get_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("UPDATE buy_stock SET day_high_price = %s WHERE ticker = %s", (day_high, ticker))
                            cursor.execute("UPDATE sell_stock SET day_high_price = %s WHERE ticker = %s AND close_yn='N'", (day_high, ticker))
                            conn.commit()
                except: pass
                
                # === SELL SIGNAL 1: 5분봉 Dead Cross (INDEPENDENT) ===
                sig1_manual = sell_record.get('is_manual_sell1') == 'Y'
                tgt1 = float(sell_record.get('manual_target_sell1') or 0)
                
                # Check manual target first
                if tgt1 > 0 and curr_price <= tgt1:
                    if sell_record['sell_sig1_yn'] == 'N':
                        from db import manual_update_signal
                        manual_update_signal(ticker, 'sell1', curr_price, 'Y')
                        print(f"🎯 {ticker} Sell Target 1 Met (${tgt1})")
                        log_history(manage_id, ticker, "1차청산신호", f"지정가도달(${tgt1})", curr_price)
                        sell_sounds.add(('sell1', ticker))
                elif is_5m_trend_down:
                    if sell_record['sell_sig1_yn'] == 'N':
                        if save_v2_sell_signal(ticker, 'sig1', curr_price):
                            msg_type = "5분봉 DC" if is_5m_dc else "5분봉 하락추세"
                            print(f"📉 {ticker} Sell Signal 1 ON ({msg_type})")
                            log_history(manage_id, ticker, "1차청산신호", msg_type, curr_price)
                            sell_sounds.add(('sell1', ticker))
                else:
                    if sell_record['sell_sig1_yn'] == 'Y' and not sig1_manual:
                        try:
                            from db import manual_update_signal
                            manual_update_signal(ticker, 'sell1', 0, 'N')
                            print(f"📈 {ticker} Sell Signal 1 OFF (trend recovered)")
                        except: pass
                
                # === SELL SIGNAL 2: Trailing Stop / Target (INDEPENDENT) ===
                sig2_manual = sell_record.get('is_manual_sell2') == 'Y'
                tgt2 = float(sell_record.get('manual_target_sell2') or 0)
                
                # Conditions for sig2
                is_tgt2_met = (tgt2 > 0 and curr_price <= tgt2)
                is_sig2_met = is_tgt2_met or is_trailing_stop
                sig2_reason = f"지정가(${tgt2})" if is_tgt2_met else f"Trailing Stop (High: ${day_high:.2f})"
                
                if is_sig2_met:
                    if sell_record['sell_sig2_yn'] == 'N':
                        from db import manual_update_signal
                        manual_update_signal(ticker, 'sell2', curr_price, 'Y')
                        print(f"🎯 {ticker} Sell Signal 2 ON ({sig2_reason})")
                        log_history(manage_id, ticker, "2차청산신호", sig2_reason, curr_price)
                        sell_sounds.add(('sell2', ticker))
                else:
                    if sell_record['sell_sig2_yn'] == 'Y' and not sig2_manual:
                        try:
                            from db import manual_update_signal
                            manual_update_signal(ticker, 'sell2', 0, 'N')
                            print(f"📈 {ticker} Sell Signal 2 OFF (above stop)")
                        except: pass
                
                # === SELL SIGNAL 3: Manual Target (INDEPENDENT) ===
                sig3_manual = sell_record.get('is_manual_sell3') == 'Y'
                tgt3 = float(sell_record.get('manual_target_sell3') or 0)
                
                if tgt3 > 0 and curr_price <= tgt3:
                    if sell_record['sell_sig3_yn'] == 'N':
                        from db import manual_update_signal
                        manual_update_signal(ticker, 'sell3', curr_price, 'Y')
                        print(f"🎯 {ticker} Sell Signal 3 ON (${tgt3})")
                        log_history(manage_id, ticker, "3차청산신호", f"지정가도달(${tgt3})", curr_price)
                        sell_sounds.add(('sell3', ticker))
                # No auto-reset for sell3 (purely target-based)
                
                # === SEND SELL SMS (최대 1개만 - 우선순위: 3 > 2 > 1) ===
                if sell_sounds:
                    sms_time = get_current_time_str_sms()
                    if ('sell3', ticker) in sell_sounds:
                        send_sms(ticker, "3차청산", curr_price, sms_time, "최종 목표가 도달")
                    elif ('sell2', ticker) in sell_sounds:
                        send_sms(ticker, "2차청산", curr_price, sms_time, "손절/이익실현")
                    elif ('sell1', ticker) in sell_sounds:
                        send_sms(ticker, "1차청산", curr_price, sms_time, "5분봉 하락추세")
                
                # === Price Level Alerts ===
                try:
                    from db import get_price_levels, set_price_level_triggered
                    active_levels = get_price_levels(ticker)
                    for lvl in active_levels:
                        if lvl['is_active'] == 'Y' and lvl['triggered'] == 'N':
                            l_type = lvl['level_type']
                            l_price = float(lvl['price'])
                            
                            should_trigger = False
                            if l_type == 'BUY' and curr_price >= l_price:
                                should_trigger = True
                            elif l_type == 'SELL' and curr_price <= l_price:
                                should_trigger = True
                            
                            if should_trigger:
                                set_price_level_triggered(ticker, l_type, lvl['stage'])
                                print(f"🔔 {ticker} Alert: {l_type} #{lvl['stage']} @ ${l_price}")
                except Exception as e:
                    pass  # Silent fail for alerts


        except Exception as e:
            print(f"❌ Error analyzing {ticker}: {e}")
            import traceback
            traceback.print_exc()

    print(f"[{datetime.now()}] V2 Analysis Complete.")

# ==========================================
# GLOBAL CACHE & HELPERS (Moved to End)
# ==========================================
_LATEST_REPORT = None

def get_cached_report():
    """Returns the last calculated analysis report or None."""
    global _LATEST_REPORT
    return _LATEST_REPORT

def stitch_kis_candles(ticker, yf_df, interval_min):
    """
    Fetches missing candles from KIS API and appends/overwrites YFinance DF.
    """
    from kis_api_v2 import kis_client
    try:
        # Fetch recent candles from KIS (Default returns 30 candles)
        print(f"    🧵 Stitching {ticker} (Interval {interval_min}m)...")
        candles = kis_client.get_minute_candles(ticker, interval_min=interval_min)
        if not candles: return yf_df
        
        # Convert to DataFrame
        new_data = []
        kst = pytz.timezone('Asia/Seoul')
        utc = pytz.timezone('UTC')
        
        for c in candles:
            # Parse KST Time (kymd + khms)
            dt_str = c['kymd'] + c['khms']
            dt_kst = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
            dt_kst = kst.localize(dt_kst)
            
            # Convert to UTC (to match YFinance usually)
            dt_target = dt_kst.astimezone(utc)
            
            new_data.append({
                'Datetime': dt_target,
                'Open': float(c['open']),
                'High': float(c['high']),
                'Low': float(c['low']),
                'Close': float(c['last']),
                'Volume': int(c['evol']) 
            })
            
        kis_df = pd.DataFrame(new_data)
        kis_df.set_index('Datetime', inplace=True)
        
        # Verify YF Timezone
        if not yf_df.empty:
             yf_tz = yf_df.index.tz
             if yf_tz:
                 kis_df.index = kis_df.index.tz_convert(yf_tz)
             else:
                 kis_df.index = kis_df.index.tz_localize(None) 
        
        # DEBUG: Check columns
        # print(f"DEBUG Stitch: YF Cols={yf_df.columns.tolist()} KIS Cols={kis_df.columns.tolist()}")
        
        # Combine: YF + KIS (KIS overwrites overlapping)
        combined = pd.concat([yf_df, kis_df])
        
        # Remove duplicates by index, keeping last (KIS)
        combined = combined[~combined.index.duplicated(keep='last')]
        combined.sort_index(inplace=True)
        
        return combined

    except Exception as e:
        print(f"Error in stitch_kis_candles: {e}")
        return yf_df
        combined = combined[~combined.index.duplicated(keep='last')]
        combined.sort_index(inplace=True)
        
        return combined

    except Exception as e:
        print(f"Stitch Logic Error ({ticker}): {e}")
        return yf_df
