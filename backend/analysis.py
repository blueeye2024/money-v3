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
# [Modified] Dynamic Ticker Management - Removed Hardcoded List
TICKER_NAMES = {} 
TARGET_TICKERS = [] # Populated from DB on runtime

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
                    # [Fix Ver 6.4.3] Prevent Stale Data Flicker (Yesterday's Close)
                    try:
                        t = yf.Ticker(ticker)
                        # Fetch today's data roughly
                        hist = t.history(period="1d", interval="1m", prepost=True)
                        
                        if not hist.empty:
                            last_row = hist.iloc[-1]
                            val = float(last_row['Close'])
                            
                            # Valid Time Check (NY Time)
                            ny_now = datetime.now(pytz.timezone('America/New_York'))
                            data_time = hist.index[-1]
                            if data_time.tzinfo is None:
                                data_time = pytz.utc.localize(data_time).astimezone(pytz.timezone('America/New_York'))
                            else:
                                data_time = data_time.astimezone(pytz.timezone('America/New_York'))

                            # If data is from today (or very recent if crossing midnight), accept it
                            # If date mismatch (e.g. yesterday's close), SKIP update to avoid dip
                            if data_time.date() == ny_now.date():
                                change = 0.0
                                # Try to get prev close from info or history calc
                                try: 
                                    prev_close = float(t.info.get('previousClose', 0))
                                    if prev_close > 0:
                                        change = ((val - prev_close) / prev_close) * 100
                                except: pass

                                data_list.append({
                                    'ticker': ticker,
                                    'name': name,
                                    'price': val,
                                    'change': change
                                })
                                print(f"  ⚠️ YF Fallback (Active): {ticker} = ${val:.2f}")
                            else:
                                print(f"  🛑 YF Fallback Stale (Skipped): {ticker} (Data: {data_time.strftime('%H:%M')} vs Now: {ny_now.strftime('%H:%M')})")
                        else:
                             print(f"  ❌ YF Fallback Empty: {ticker}")
                    except Exception as yf_e:
                        print(f"  ❌ YF Fallback Error: {yf_e}")
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
    if tickers:
        target_list = tickers
    else:
        # Load from DB dynamically
        from db import get_managed_stocks
        try:
             stocks = get_managed_stocks()
             target_list = [s['ticker'] for s in stocks]
        except:
             target_list = []
    
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
                
                if df is None: df = pd.DataFrame()
                
                # [STITCH KIS CANDLES for 30m] (Fix Daytime Gap)
                # Even if YF failed (empty), try KIS
                try:
                    df = stitch_kis_candles(ticker, df, 30)
                except Exception as e: print(f"Stitch 30m Error {ticker}: {e}")

                if df is not None and not df.empty: 
                    # [Ver 5.8] Regression Protection
                    # Check against GLOBAL cache to avoid overwriting recent data with old data (if KIS fails)
                    if "30m" in _DATA_CACHE and _DATA_CACHE["30m"] is not None and ticker in _DATA_CACHE["30m"]:
                         try:
                             last_old = _DATA_CACHE["30m"][ticker].index[-1]
                             last_new = df.index[-1]
                             # Ensure Timezone compatibility before comparing
                             if last_old.tzinfo is not None and last_new.tzinfo is None:
                                 last_new = last_new.tz_localize(last_old.tzinfo)
                             
                             if last_new < last_old:
                                  print(f"    🛡️ Protected {ticker}: New {last_new} < Old {last_old}. Keeping Cache.")
                                  df = _DATA_CACHE["30m"][ticker]
                         except Exception as e:
                             print(f"    ⚠️ Protection Check Error: {e}")

                    # Mem Cache
                    temp_30m[ticker] = df
                    # DB Save (Deprecated No-op but kept for interface)
                    # Note: If we reverted to Old Cache, we probably shouldn't re-save?
                    # Or saving is harmless (ONOT_APPLICABLE UPDATE).
                    print(f"    💾 DEBUG: Calling save_market_candles for {ticker} 30m. Len={len(df)}")
                    save_market_candles(ticker, '30m', df, 'yfinance')
            except Exception as e: print(f"Save 30m Error {ticker}: {e}")

            # Save 5m
            try:
                df = None
                if isinstance(new_5m.columns, pd.MultiIndex) and ticker in new_5m.columns: df = new_5m[ticker]
                elif not isinstance(new_5m.columns, pd.MultiIndex) and len(target_list) == 1: df = new_5m
                
                if df is None: df = pd.DataFrame()

                # [STITCH KIS CANDLES]
                try:
                    df = stitch_kis_candles(ticker, df, 5)
                except Exception as e: print(f"Stitch 5m Error {ticker}: {e}")

                if df is not None and not df.empty: 
                    # [Ver 5.8] Regression Protection (5m)
                    if "5m" in _DATA_CACHE and _DATA_CACHE["5m"] is not None and ticker in _DATA_CACHE["5m"]:
                         try:
                             last_old = _DATA_CACHE["5m"][ticker].index[-1]
                             last_new = df.index[-1]
                             if last_old.tzinfo is not None and last_new.tzinfo is None:
                                 last_new = last_new.tz_localize(last_old.tzinfo)
                             
                             if last_new < last_old:
                                  print(f"    🛡️ Protected {ticker} (5m): New {last_new} < Old {last_old}. Keeping Cache.")
                                  df = _DATA_CACHE["5m"][ticker]
                         except Exception as e: print(f"Protection Error 5m: {e}")

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
    if target_list:
        pass
    else:
        # Load from DB dynamically
        from db import get_managed_stocks
        try:
             stocks = get_managed_stocks()
             target_list = [s['ticker'] for s in stocks]
        except:
             target_list = []
    
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

# [Ver 6.5.8] 박스권 탈출 지수 (Box Breakout Index)
def calculate_bbi(df, period=20):
    """
    박스권 탈출 지수 계산
    범위: -10 (극심한 횡보) ~ +10 (강력한 돌파)
    
    Args:
        df: DataFrame with Close, High, Low columns
        period: BBW 평균 계산 기간 (default: 20)
    Returns:
        dict: {'bbi': float, 'adx': float, 'bbw_ratio': float, 'status': str}
    """
    try:
        close = df['Close']
        high = df['High']
        low = df['Low']
        
        if len(df) < 30:
            return {'bbi': 0, 'adx': 0, 'bbw_ratio': 1.0, 'status': '데이터 부족'}
        
        # [Fix] Case-insensitive column access
        close = df['Close'] if 'Close' in df.columns else df['close']
        high = df['High'] if 'High' in df.columns else df['high']
        low = df['Low'] if 'Low' in df.columns else df['low']
        
        # 1. ADX 14일 - 추세 강도
        adx_df = ta.adx(high, low, close, length=14)
        adx = float(adx_df['ADX_14'].iloc[-1]) if adx_df is not None and 'ADX_14' in adx_df.columns else 20.0
        
        # 2. 볼린저 밴드폭 (BBW)
        bb = ta.bbands(close, length=20, std=2)
        if bb is not None and 'BBU_20_2.0' in bb.columns:
            bbw = (bb['BBU_20_2.0'] - bb['BBL_20_2.0']) / bb['BBM_20_2.0']
            current_bbw = float(bbw.iloc[-1])
            avg_bbw = float(bbw.tail(period).mean())
        else:
            current_bbw = 0.05
            avg_bbw = 0.05
        
        # 3. Trend Factor (0~10)
        trend_factor = max(0, min(10, ((adx - 15) / 20) * 10))
        
        # 4. Vol Factor (0~10)
        bbw_ratio = current_bbw / avg_bbw if avg_bbw > 0 else 1.0
        vol_factor = max(0, min(10, ((bbw_ratio - 0.8) / 0.7) * 10))
        
        # 5. BBI 계산
        bbi = round((trend_factor + vol_factor) - 10, 2)
        
        # 6. 상태 텍스트
        if bbi <= -7:
            status = '극심한 박스권'
        elif bbi <= -1:
            status = '일반 횡보'
        elif bbi <= 3:
            status = '변동성 시작'
        elif bbi <= 7:
            status = '박스권 돌파'
        else:
            status = '강력한 슈팅'
        
        return {
            'bbi': bbi,
            'adx': round(adx, 2),
            'bbw_ratio': round(bbw_ratio, 2),
            'status': status
        }
    except Exception as e:
        print(f"BBI Calculation Error: {e}")
        return {'bbi': 0, 'adx': 0, 'bbw_ratio': 1.0, 'status': '계산 오류'}

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

# [Ver 7.2.5] Pure Signal Calculation (No DB Dependency)
def calculate_v2_signals_pure(df_30, df_5, daily_change=0.0):
    """
    Calculate V2 Signals purely from DataFrames for Objective Scoring.
    Returns logic state: step1, step2, step3 (all booleans)
    Step 2 Logic: Daily Change >= +2.0% (Vanguard Condition)
    """
    res = {'step1': False, 'step2': False, 'step3': False}
    if df_5 is None or df_5.empty or df_30 is None or df_30.empty:
        return res
        
    try:
        # 1. Step 1 (5m Trend)
        # Check if MA10 > MA30 on 5m
        last_5 = df_5.iloc[-1]
        
        # Ensure MAs exist (calculated in analyze_ticker usually, but let's be safe)
        ma10_5 = last_5.get('SMA10', 0) or last_5.get('ma10', 0)
        ma30_5 = last_5.get('SMA30', 0) or last_5.get('ma30', 0)
        
        # If columns missing, re-calc for last row? 
        # analyze_ticker adds 'SMA10', 'SMA30'. run_v2 adds 'ma10', 'ma30'.
        # Let's support both or recalc if 0.
        if ma10_5 == 0: ma10_5 = df_5['Close'].tail(10).mean()
        if ma30_5 == 0: ma30_5 = df_5['Close'].tail(30).mean()
        
        res['step1'] = (ma10_5 > ma30_5)
        
        # 2. Step 3 (30m Trend - Sequence is 1->2->3 but logic checks 3 independently)
        last_30 = df_30.iloc[-1]
        ma10_30 = last_30.get('SMA10', 0) or last_30.get('ma10', 0)
        ma30_30 = last_30.get('SMA30', 0) or last_30.get('ma30', 0)
        
        if ma10_30 == 0: ma10_30 = df_30['Close'].tail(10).mean()
        if ma30_30 == 0: ma30_30 = df_30['Close'].tail(30).mean()
        
        res['step3'] = (ma10_30 > ma30_30)
        
        # 3. Step 2 (Vanguard / Momentum)
        # Definition from '06_SOXL_SOXS_Ver5.3.2_상세설계.md': Daily Change >= +2.0%
        res['step2'] = (daily_change >= 2.0)
        
    except Exception as e:
        print(f"Pure Signal Calc Error: {e}")
        
    return res

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

    # [Ver 5.8.4] Inject Pre-Market Strategy from Daily Report
    try:
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")
        from db import get_connection
        with get_connection() as conn:
            with conn.cursor() as cursor:
                sql = "SELECT pre_market_strategy FROM daily_reports WHERE report_date = %s"
                cursor.execute(sql, (today_str,))
                row = cursor.fetchone()
                if row and row['pre_market_strategy']:
                    if 'details' not in regime_info:
                        regime_info['details'] = {}
                        
                    # Override comment with Strategy
                    regime_info['details']['comment'] = row['pre_market_strategy']
                    print(f"✅ Injected Pre-Market Strategy: {row['pre_market_strategy'][:30]}...")
    except Exception as e:
        print(f"Strategy Injection Error: {e}")
    
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
        "indices": clean_nan(market_data), # [Ver 6.9.1] Provide raw list for MarketInsight (UPRO etc)
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




def check_triple_filter(ticker, data_30m, data_5m, override_price=None, simulation_mode=False, simulation_context=None):
    """
    [Refactored V5.6] Single Source of Truth
    - READ-ONLY from DB (Dashboard Mode)
    - DYNAMIC CALCULATION from DataFrames (Simulation Mode)
    """
    from db import fetch_signal_status_dict, get_global_config
    import datetime
    
    # 1. Initialize Result Dict
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
        "name": TICKER_NAMES.get(ticker, ticker), 
        "sounds": [],
        "price_alerts": [],
        "ma12": 0.0
    }

    if simulation_mode:
        # [Simulation Mode] Calculate Signals from Dataframes 
        # (Used by Lab / Backtest)
        try:
            # Context unpacking
            sim_ctx = simulation_context or {}
            prev_close = sim_ctx.get('prev_close', 0.0)
            
            # --- Get Data Subsets (Last Row) ---
            df5 = None
            if isinstance(data_5m, dict): df5 = data_5m.get(ticker)
            else: df5 = data_5m
            
            df30 = None
            if isinstance(data_30m, dict): df30 = data_30m.get(ticker)
            else: df30 = data_30m
            
            curr_price = 0.0
            if df5 is not None and not df5.empty:
                curr_price = float(df5['Close'].iloc[-1])
            elif override_price:
                 curr_price = float(override_price)
                 
            result['current_price'] = curr_price
            
            # --- Step 1: 5m Trend (MA10 > MA30) ---
            is_step1 = False
            if df5 is not None and not df5.empty:
                # Require MA columns to be present (uploaded)
                # Flexible case: 'MA10' or 'ma10'
                ma10_col = 'MA10' if 'MA10' in df5.columns else 'ma10'
                ma30_col = 'MA30' if 'MA30' in df5.columns else 'ma30'
                
                if ma10_col in df5.columns and ma30_col in df5.columns:
                     m10 = float(df5[ma10_col].iloc[-1])
                     m30 = float(df5[ma30_col].iloc[-1])
                     if m10 > m30: is_step1 = True
            
            result['step1'] = is_step1
            result['step1_status'] = "진입 타점 (5m 정배열)" if is_step1 else "진입 대기"
            if not is_step1: result['step1_color'] = "yellow"

            # --- Step 2: Box Breakout / Momentum ---
            # Condition: Current Price > Prev Close * 1.02 Or Daily Change > 2.0%
            is_step2 = False
            daily_change = 0.0
            
            if prev_close > 0:
                daily_change = ((curr_price - prev_close) / prev_close) * 100
            elif 'ChangePct' in df5.columns:
                 # Fallback to column if exists (might be wrong reference but better than 0)
                 daily_change = float(df5['ChangePct'].iloc[-1])
            
            result['daily_change'] = round(daily_change, 2)
            
            # Threshold: 1.5% as requested/implied?
            # Prime Guide says "Box Breakout". Simplified to Momentum > 1~2%.
            # Using 1.5% as reasonable breakout proxy without Box lines.
            if daily_change >= 1.5:
                is_step2 = True
                
            result['step2'] = is_step2
            result['step2_status'] = "수급 돌파 (>1.5%)" if is_step2 else "모멘텀 부족"
            
            # --- Step 3: 30m Trend (MA10 > MA30) ---
            is_step3 = False
            if df30 is not None and not df30.empty:
                ma10_col = 'MA10' if 'MA10' in df30.columns else 'ma10'
                ma30_col = 'MA30' if 'MA30' in df30.columns else 'ma30'
                
                if ma10_col in df30.columns and ma30_col in df30.columns:
                     m10 = float(df30[ma10_col].iloc[-1])
                     m30 = float(df30[ma30_col].iloc[-1])
                     if m10 > m30: is_step3 = True
            
            result['step3'] = is_step3
            result['step3_status'] = "추세 확정 (30m 정배열)" if is_step3 else "추세 미확보"
            if not is_step3: result['step3_color'] = "yellow"

            # Final
            result['final'] = (result['step1'] and result['step2'] and result['step3'])
            
            # [Sell Signal Simulation]
            # Simple Dead Cross on 5m
            if df5 is not None and not df5.empty:
                ma10_col = 'MA10' if 'MA10' in df5.columns else 'ma10'
                ma30_col = 'MA30' if 'MA30' in df5.columns else 'ma30'
                if ma10_col in df5.columns and ma30_col in df5.columns:
                     m10 = float(df5[ma10_col].iloc[-1])
                     m30 = float(df5[ma30_col].iloc[-1])
                     if m10 < m30:
                         result['is_sell_signal'] = True
            
            # Metrics
            if df30 is not None and not df30.empty:
                 result['new_metrics'] = calculate_market_intelligence(df30)

            return result

        except Exception as e:
            print(f"Simulation Error {ticker}: {e}")
            # Fallback to empty result (safe)
            pass

    print(f"DEBUG: Checking {ticker} (Read-Only Mode / Dashboard)")

    try:
        # 2. Fetch Truth from DB
        db_status = fetch_signal_status_dict(ticker)
        buy_db = db_status.get('buy')
        sell_db = db_status.get('sell')
        
        # 3. Get Current Price (for Display only)
        # Try KIS first, then DF
        current_price = 0.0
        daily_change = 0.0
        
        if override_price is not None:
             current_price = float(override_price)
             # calc approx change? ignore for now or calc if prev avail
        else:
            # Try KIS Cache or Live
            from kis_api_v2 import kis_client
            kis_data = kis_client.get_price(ticker)
            if kis_data and kis_data.get('price', 0) > 0:
                 current_price = float(kis_data['price'])
                 daily_change = float(kis_data.get('rate', 0))
             
        # [Ver 5.8.6] User Request: Day High based on Today's Close (Max Close / Body High)
        # Instead of High (Wick), we use the highest Close price of the day.
        # [Fix] Filter for TODAY's data only (Last available date in DF)
        high_candidates = []
        try:
             # 1. Current Price (always a candidate)
             if current_price > 0: high_candidates.append(current_price)
             
             # 2. 5m Candles Max Close (Filtered by Date)
             df5 = None
             if isinstance(data_5m, dict): df5 = data_5m.get(ticker)
             elif hasattr(data_5m, 'columns'): df5 = data_5m
             if df5 is not None and not df5.empty:
                 # Filter: Last Day Only
                 try:
                     last_date = df5.index[-1].normalize() # 00:00:00 of last day
                 except: 
                     # Fallback if index is not DatetimeIndex
                     if 'candle_time' in df5.columns:
                         last_date = pd.to_datetime(df5['candle_time'].iloc[-1]).normalize()
                         # Temporary Index for filtering
                         df5 = df5.set_index('candle_time', drop=False)
                     else:
                         last_date = None
                 
                 if last_date:
                     today_df5 = df5.loc[df5.index >= last_date]
                     if not today_df5.empty:
                         # Use case-insensitive column
                         c_col = 'Close' if 'Close' in today_df5.columns else 'close'
                         high_candidates.append(float(today_df5[c_col].max()))
                 
             # 3. 30m Candles Max Close (Filtered by Date)
             df30 = None
             if isinstance(data_30m, dict): df30 = data_30m.get(ticker)
             elif hasattr(data_30m, 'columns'): df30 = data_30m
             if df30 is not None and not df30.empty:
                 try:
                     last_date_30 = df30.index[-1].normalize()
                 except: 
                     if 'candle_time' in df30.columns:
                         last_date_30 = pd.to_datetime(df30['candle_time'].iloc[-1]).normalize()
                         df30 = df30.set_index('candle_time', drop=False)
                     else:
                         last_date_30 = None

                 if last_date_30:
                     today_df30 = df30.loc[df30.index >= last_date_30]
                     if not today_df30.empty:
                         c_col = 'Close' if 'Close' in today_df30.columns else 'close'
                         high_candidates.append(float(today_df30[c_col].max()))
                 
        except Exception as e:
            print(f"Max Close Calc Error {ticker}: {e}")
            
        # Set Day High to Max Close
        if high_candidates:
            result['day_high'] = max(high_candidates)
        else:
            result['day_high'] = current_price

        # API High (Wick) is ignored for "Day High" display/logic as per request, 
        # but we might want to keep it if candles are empty? 
        # The candidates include current_price, so it's safe.
        
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
            
        # 7. MA12 Calculation for Frontend Display
        # [Ver 7.6] Add MA12 to result for Dashboard Action Plan "Maintenance" Price
        print(f"DEBUG {ticker} Checking DF5: {type(df5)} Empty={df5.empty if df5 is not None else 'None'}")
        
        if df5 is not None and not df5.empty:
            try:
                ma12_series = df5['Close'].rolling(window=12).mean()
                val = float(ma12_series.iloc[-1])
                
                if pd.isna(val):
                    val = 0.0
                    print(f"DEBUG {ticker} MA12 is NaN (Len: {len(df5)}) Head: {df5['Close'].head().tolist()}")
                else:
                    print(f"DEBUG {ticker} MA12 Calculated: {val} (Len: {len(df5)})")
                    
                result['ma12'] = val
            except Exception as e:
                print(f"DEBUG {ticker} MA12 Calc Error: {e}")
                result['ma12'] = 0.0
        else:
            print(f"DEBUG {ticker} DF5 Missing or Empty - MA12 Skipped")
            
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
    if len(df) < 12: return {} # Absolute minimum for MA12
    
    result = {}
    try:
        # [Ver 8.0.7] Robust Calculation (Partial Data Support)
        
        # 1. MA12 (Priority for Signal 2)
        if len(df) >= 12:
            ma12 = df['Close'].rolling(window=12).mean()
            result['ma12'] = ma12.iloc[-1]
            
        # 2. RSI (14)
        if len(df) >= 15: # 14 + 1 for diff
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            result['rsi'] = df['RSI'].iloc[-1]
        
        # 3. MACD (26)
        if len(df) >= 26:
            exp12 = df['Close'].ewm(span=12, adjust=False).mean()
            exp26 = df['Close'].ewm(span=26, adjust=False).mean()
            macd = exp12 - exp26
            signal = macd.ewm(span=9, adjust=False).mean()
            result['macd'] = macd.iloc[-1]
            result['macd_sig'] = signal.iloc[-1]

        return result
    except Exception as e:
        print(f"Tech Calc Error: {e}")
        return result

def calculate_market_energy(target_change, upro_change, is_bull=True):
    """
    [Jian 1.1] Market Energy Score Calculation
    Logic:
    - Relation Index (RI) = (Target Change / UPRO Change) * 100
    - Raw Energy = (RI - 100) / 20
    - If UPRO Change < 0 (Bear Market), Energy uses inverse sign (or logic tweak depending on implementation)
      Front-end: if (uproChange < 0) rawEnergy = -rawEnergy;
      Then Energy = trunc(rawEnergy) (for Bull) or trunc(-rawEnergy) (for Bear)
    """
    if abs(upro_change) < 0.05: return 0 # Avoid division by zero equivalent
    
    relation_index = (target_change / upro_change) * 100
    raw_energy = (relation_index - 100) / 20.0
    
    if upro_change < 0:
        raw_energy = -raw_energy
        
    # Clamp -10 to 10
    raw_energy = max(-10, min(10, raw_energy))
    
    # Final Score based on Ticker Type
    if is_bull:
        return int(raw_energy)
    else:
        return int(-raw_energy)

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
    elif score >= 60:
        action_header = "✅ 매수 (BUY)"
        action_detail = "1차(5분봉) 신호 발생 시 20% 정찰병 선진입이 유리합니다. 단, 5분봉 데드크로스 발생 시 즉시 이탈(청산)해야 합니다."
    elif score <= 30:
        action_header = "⚠️ 관망/매도 (WAIT/SELL)"
        action_detail = "진입 근거가 부족합니다. 무리한 진입보다 현금 비중을 늘리고 다음 파동을 기다리십시오."
    elif res.get('step2_color') == 'orange':
        action_header = "🚨 긴급 탈출 (STOP LOSS)"
        action_detail = "원금 보전을 최우선으로 하십시오. 즉시 비중을 축소하거나 전량 청산하는 것을 권장합니다."
    else: # 40~59
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


def calculate_holding_score(res, tech, v2_buy=None, v2_sell=None, bbi_score=0, energy_score=0, strict_sum=False):
    """
    V4.0 안티그래비티 스코어 시스템 (Antigravity Score System)
    strict_sum: If True, disables penalties and range capping (returns raw sum of visible components).
    """
    if not res: return {"score": 0, "breakdown": {}, "evaluation": "데이터 부족"}

    # Initialize Breakdown
    breakdown = {
        "cheongan": 0,    # 청안 지수 (V2 Signals)
        "rsi": 0,         # RSI 점수
        "macd": 0,        # MACD 점수
        "vol": 0,         # Vol Ratio 점수
        "atr": 0,         # ATR 점수
        "bbi": 0,         # [Ver 6.5.8] BBI 점수
        "energy": 0,      # [Ver 7.2] Market Energy
        "total": 0
    }
    
    breakdown['energy'] = energy_score
    
    # ================================================
    # 1. 청안 지수 (V2 Signal Base) - Max 60점
    # ================================================
    cheongan_score = 0
    sig1 = v2_buy and v2_buy.get('buy_sig1_yn') == 'Y'
    sig2 = v2_buy and v2_buy.get('buy_sig2_yn') == 'Y'
    sig3 = v2_buy and v2_buy.get('buy_sig3_yn') == 'Y'
    
    # [Jian 1.1] Cumulative Scoring
    if sig1: cheongan_score += 20
    if sig2: cheongan_score += 20  # 2차 20점 (User Feedback)
    if sig3: cheongan_score += 20  # 3차 20점
    
    breakdown['cheongan'] = cheongan_score
    
    # ================================================
    # 1-B. 매도 감점 (Sell Penalty) - DISABLED in strict_sum mode
    # ================================================
    # ================================================
    # 1-B. 매도 감점 (Sell Penalty) - DISABLED (User Request Ver 7.6)
    # ================================================
    sell_penalty = 0
    # if not strict_sum:
    #     rsi = tech.get('rsi', 50)
    #     is_30m_dc = tech.get('is_30m_dc', False)  # 30분봉 데드크로스
    #     
    #     if v2_sell:
    #         if v2_sell.get('sell_sig3_yn') == 'Y':
    #             sell_penalty = -30  # Level 3: 추세 이탈 확정
    #         elif is_30m_dc or rsi < 30:
    #             sell_penalty = -20  # Level 2: 강력 경고 (30분 DC 또는 과매도)
    #         elif v2_sell.get('sell_sig1_yn') == 'Y' and rsi < 45:
    #             sell_penalty = -10  # Level 1: 경고 (5분 DC + 약세 RSI)
    #         elif v2_sell.get('sell_sig1_yn') == 'Y':
    #             sell_penalty = -5   # 5분 DC만 (RSI 양호 시 가벼운 감점)
    
    breakdown['sell_penalty'] = sell_penalty
    
    # ================================================
    # 2. 안티그래비티 보조지표 (+32 ~ -32점)
    # ================================================
    rsi = tech.get('rsi', 50)
    macd = tech.get('macd', 0)
    macd_sig = tech.get('macd_sig', 0)
    
    new_metrics = res.get('new_metrics', {})
    vol_ratio = new_metrics.get('vol_ratio', 1.0)
    atr = new_metrics.get('atr', 0)
    current_price = res.get('current_price', 0)
    daily_change = res.get('daily_change', 0)
    
    # ---- A. RSI 채점 (+8 ~ -4) ----
    rsi_score = 0
    if 55 <= rsi < 70:
        rsi_score = 8    # 상승 추세
    elif 70 <= rsi < 80:
        rsi_score = 4    # 경계 구간
    elif 45 <= rsi < 55:
        rsi_score = 0    # 중립
    elif 30 <= rsi < 45:
        rsi_score = -4   # 하락 추세
    elif rsi >= 80:
        rsi_score = -4   # 과열
    elif rsi < 30:
        rsi_score = -4   # 과매도
    breakdown['rsi'] = rsi_score
    
    # ---- B. MACD 채점 (+8 ~ -8) ----
    macd_score = 0
    if macd > macd_sig and macd > 0:
        macd_score = 8    # 골든크로스 + 양수
    elif macd > macd_sig:
        macd_score = 4    # 골든크로스
    elif macd < macd_sig and macd >= 0:
        macd_score = -4   # 데드크로스 시작
    elif macd < 0 and macd < macd_sig:
        macd_score = -8   # 강력 하락
    breakdown['macd'] = macd_score
    
    # ---- C. Vol Ratio 채점 (+8 ~ -8) ----
    vol_score = 0
    if vol_ratio > 2.5 and daily_change < 0:
        vol_score = -8    # 투매
    elif vol_ratio > 2.0 and daily_change < 0:
        vol_score = -8    # 투매
    elif vol_ratio > 2.0 and daily_change > 0 and rsi > 70:
        vol_score = 0     # 경계
    elif vol_ratio > 2.0 and daily_change > 0:
        vol_score = 8     # 강력 매수세
    elif vol_ratio > 1.5 and daily_change > 0:
        vol_score = 3     # 평균 이상
    elif vol_ratio > 1.0:
        vol_score = 0     # 중립
    elif 0.5 < vol_ratio <= 0.8:
        vol_score = -3    # 매수세 부족
    breakdown['vol'] = vol_score
    
    # ---- D. ATR 채점 (+8 ~ -8) ----
    atr_score = 0
    atr_ratio = (atr / current_price) if current_price > 0 else 0
    
    if daily_change > 1 and atr_ratio > 0.02:
        atr_score = 8     # 강한 추세적 돌파
    elif daily_change > 0:
        atr_score = 4     # 완만한 우상향
    elif daily_change < 0 and atr_ratio > 0.02:
        atr_score = -4    # 공포 섞인 하락
    elif daily_change < -3 and atr_ratio > 0.03:
        atr_score = -8    # 패닉셀 구간
    breakdown['atr'] = atr_score
    
    # [Ver 6.5.8] F. BBI 채점 (+10 ~ -10)
    breakdown['bbi'] = bbi_score

    # ================================================
    # 3. 총점 계산
    # ================================================
    # [Ver 7.6] BBI Excluded from Total Score (Reference Only)
    indicator_total = breakdown['rsi'] + breakdown['macd'] + breakdown['vol'] + breakdown['atr'] + breakdown['energy']
    sell_penalty = breakdown.get('sell_penalty', 0)
    total_score = breakdown['cheongan'] + indicator_total + sell_penalty
    
    # 범위 제한: -80 ~ 100 (Disable in strict_sum)
    if not strict_sum:
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
        "new_metrics": new_metrics,
        "cheongan_details": {
            "sig1": 20 if sig1 else 0,
            "sig2": 20 if sig2 else 0,
            "sig3": 20 if sig3 else 0,
            "energy": energy_score,
            "sig2_price": res.get('ma12', 0)
        }
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
    bd_text = f"[채점표] 추세 +{breakdown.get('cheongan', 0)} | 지표 "
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
        if v2_stage: comment += f"V2 시스템이 {v2_stage} 상태입니다. "
        comment += f"추세와 보조지표가 모두 상승을 가리킵니다.\n"
        comment += "💡 수익을 극대화(Let profits run)하십시오."
        
    elif score >= 60:
        comment += f"✅ [Action] 매수 관점 (Buy). 상승 모멘텀이 유효합니다."
        if v2_stage: comment += f" (V2: {v2_stage})"
        comment += "\n"
        
        tech_sum = breakdown.get('macd', 0) + breakdown.get('rsi', 0) + breakdown.get('vol', 0)
        if tech_sum > 0: comment += "기술적 지표가 긍정적입니다. "
        comment += f"💡 분할 매수로 접근하십시오."
        if vol_ratio < 0.8: comment += " (단, 거래량 부족 주의)"
        
    elif score >= 40:
        comment += f"⏳ [Action] 관망/중립 (Hold). "
        if v2_stage: comment += f" (V2: {v2_stage})"
        if breakdown.get('penalty', 0) > 0: comment += f"패널티 요소(-{breakdown['penalty']})가 있어 진입을 보류합니다.\n"
        else: comment += "뚜렷한 상승 신호가 부족합니다.\n"
        comment += "💡 다음 V2 신호를 기다리십시오."
        
    else: # Score < 40
        comment += f"⚠️ [Action] 매도/리스크 관리 (Sell). "
        if v2_stage: comment += f" (V2: {v2_stage})"
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
    Process auto trading logic (Ver 7.0 Score-Based)
    - Entry: Score >= 70 AND No Open Trade
    - Exit: Score < 50 AND Open Trade
    """
    try:
        from db import get_open_trade, create_trade, close_trade
        
        # Check current status
        open_trade = get_open_trade(ticker)
        score = result_info.get('score', 0)
        
        # 1. Entry Logic (Score >= 70)
        if not open_trade:
            if score >= 70:
                create_trade(ticker, current_price, current_time)
                print(f"🚀 [AUTO BUY] {ticker} at {current_price} (Score: {score})")
            
        # 2. Exit Logic (Score < 50)
        elif open_trade:
            # Only exit if score drops below 50
            if score < 50:
                 close_trade(ticker, current_price, current_time)
                 print(f"📉 [AUTO SELL] {ticker} at {current_price} (Score: {score})")
                 
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
        
        # [Ver 8.0.6] Ensure MA12 is in results before scoring
        results[t]['ma12'] = techs[t].get('ma12', 0)
        
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
        v2_buy_info = None
        v2_sell_info = None
        if t in ['SOXL', 'SOXS']:
             v2_buy_info = results[t].get('v2_buy')
             v2_sell_info = results[t].get('v2_sell')

        # 1. Calculate Score
        # [Ver 6.5.8] Calculate BBI for Score Weighting
        bbi_score = 0
        try:
            if t in ['SOXL', 'SOXS'] and df_30 is not None:
                bbi_res = calculate_bbi(df_30)
                bbi_score = bbi_res.get('bbi', 0)

        except Exception as e:
            print(f"BBI Calc Error {t}: {e}")

        # [Ver 7.6.2] Calculate Energy Score (Ported from Frontend MarketInsight.jsx)
        energy_score = 0
        try:
            if t in ['SOXL', 'SOXS']:
                upro_val = results.get('UPRO', {}).get('daily_change', 0)
                soxl_val = results.get('SOXL', {}).get('daily_change', 0)
                
                relation_index = 0
                if abs(upro_val) > 0.05:
                    relation_index = (soxl_val / upro_val) * 100
                    
                raw_energy = (relation_index - 100) / 20.0
                if upro_val < 0: raw_energy = -raw_energy
                
                raw_energy = max(-10, min(10, raw_energy))
                
                if t == 'SOXL':
                    energy_score = int(raw_energy)
                else: # SOXS
                    energy_score = int(-raw_energy)
        except Exception as e:
            print(f"Energy Calc Error {t}: {e}")

        # [Ver 7.5.0] Revert to DB-based Score (Honoring Latched System Signals)
        # Using pure calc caused valid past signals to be ignored.
        # DB 'buy_sigX_yn' is updated by Auto Logic based on Chart, even if Manual is On.
        # Manual Register inserts 'N' initially, so scoring is safe.
        
        score_model = calculate_holding_score(
            results[t], 
            techs[t], 
            v2_buy=results[t].get('v2_buy'), # Use DB Status
            v2_sell=results[t].get('v2_sell'), 
            bbi_score=bbi_score,
            energy_score=energy_score
        )
        scores[t] = score_model
        
        # [Ver 7.2.4] Inject Score into Results for Frontend
        results[t]['score'] = score_model.get('score', 0)
        results[t]['score_eval'] = score_model.get('evaluation', '')
        
        # [Ver 7.6.1] Inject Full Breakdown for Backend Logic (main.py Lab Save)
        results[t]['score_breakdown'] = score_model.get('breakdown', {})
        results[t]['cheongan_details'] = score_model.get('cheongan_details', {})
        
        # [Fix] Ensure Dashboard BBI matches Lab Data BBI
        if 'new_metrics' not in results[t]: results[t]['new_metrics'] = {}
        results[t]['new_metrics']['bbi'] = bbi_score
        
        # 2. Generate Guide
        # For Guide text, we might still want to know "Real Buy" status to give context?
        # But usually Guide should also be objective. 
        # However, v2_buy_info (DB) might be needed if we want to say "You are holding this". 
        # generate_expert_commentary_v2 uses v2_buy to customize message?
        # Let's check. If it uses it for 'Status: Holding', then we might want to pass DB info there.
        # But if calculate_holding_score is what determines the "Score" and "Signal Strength", we fixed that.
        
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

        # [NEW] Score Threshold Logging (60/40) - Persistent History
        # User Request: "60점 돌파 / 40점 하향 돌파 시 가격과 미국 시간 등록"
        # + [Ver 5.9.3] Auto Trading Log (System Trade)
        try:
            from db import save_signal, get_open_trade, start_trade, end_trade
            global _PREV_SCORES
            if '_PREV_SCORES' not in globals(): _PREV_SCORES = {}
            
            curr_score = score_model.get('score', 0)
            curr_price = results[t].get('current_price', 0)
            prev_score = _PREV_SCORES.get(t, None)
            prev_score = _PREV_SCORES.get(t, None)
            open_trade = get_open_trade(t)
            
            # [DEBUG]
            print(f"🕵️ [DEBUG] {t} Score: {curr_score}, Prev: {prev_score}, OpenTrade: {open_trade}")

            # --- 1. Score Crossing Log (For Audio & Signal History) ---
            if prev_score is not None:
                us_time = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-5))).strftime("%Y-%m-%d %H:%M") # EST/EDT approx
                
                # Check 60 Break (Up)
                if prev_score <= 60 and curr_score > 60:
                    msg = f"점수 60점 돌파! ({prev_score}->{curr_score}) [US: {us_time}]"
                    save_signal({
                        'ticker': t,
                        'name': "BULL TOWER" if t == 'SOXL' else "BEAR TOWER",
                        'signal_type': "SCORE_UP_60",
                        'position': msg,
                        'current_price': curr_price,
                        'signal_time_raw': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'is_sent': False,
                        'score': curr_score,
                        'interpretation': f"매수 강화구간 진입 (US {us_time})"
                    })
                    print(f"✅ {t} Score > 60 Logged")

                # Check 40 Break (Down)
                if prev_score >= 40 and curr_score < 40:
                    msg = f"점수 40점 이탈! ({prev_score}->{curr_score}) [US: {us_time}]"
                    save_signal({
                        'ticker': t,
                        'name': "BULL TOWER" if t == 'SOXL' else "BEAR TOWER",
                        'signal_type': "SCORE_DOWN_40",
                        'position': msg,
                        'current_price': curr_price,
                        'signal_time_raw': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'is_sent': False,
                        'score': curr_score,
                        'interpretation': f"매수 약화구간 진입 (US {us_time})"
                    })
                    print(f"✅ {t} Score < 40 Logged")

            # --- 2. Auto Trading Log (Persistent Table) ---
            # Buy if Score >= 60 and No Open Trade
            # Sell if Score <= 40 and Open Trade Exists
            
            open_trade = get_open_trade(t)
            
            if open_trade is None:
                if curr_score >= 60:
                    if start_trade(t, curr_price):
                        print(f"🚀 [Auto-Trade] Buy {t} at {curr_price} (Score: {curr_score})")
                        # Optional: Log Signal
                        save_signal({
                           'ticker': t,
                           'name': f"{t} SYSTEM BUY",
                           'signal_type': "AUTO_TRADE_BUY",
                           'position': f"System Buy @ {curr_price} (Score {curr_score})",
                           'current_price': curr_price,
                           'signal_time_raw': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                           'is_sent': False,
                           'score': curr_score,
                           'interpretation': "시스템 매수 진입"
                        })
            
            else: # Holding Position
                if curr_score <= 40:
                    if end_trade(t, curr_price):
                        print(f"📉 [Auto-Trade] Sell {t} at {curr_price} (Score: {curr_score})")
                        save_signal({
                           'ticker': t,
                           'name': f"{t} SYSTEM SELL",
                           'signal_type': "AUTO_TRADE_SELL",
                           'position': f"System Sell @ {curr_price} (Score {curr_score})",
                           'current_price': curr_price,
                           'signal_time_raw': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                           'is_sent': False,
                           'score': curr_score,
                           'interpretation': "시스템 매도 청산"
                        })

            # Update Previous Score
            _PREV_SCORES[t] = curr_score
            
        except Exception as e:
            print(f"Score/AutoTrade Log Error {t}: {e}")
        
    # Get Filtered History
    recent_history = get_filtered_history_v2()
    # recent_news = get_market_news_v2()
    
    # [Ver 5.8.2] Dynamic Version String
    version_str = f"Ver 8.0.7 (Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')})"
    
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
            
            # [Ver 7.6] Add MA12 for C2 Signal
            df_5['ma12'] = df_5['Close'].rolling(window=12).mean()
            ma12_5 = df_5['ma12'].iloc[-1]
            
            # [Ver 8.0.2] MA12 Zero Fix (Use previous if 0)
            if (ma12_5 is None or float(ma12_5) <= 0) and len(df_5) > 1:
                prev_ma12 = df_5['ma12'].iloc[-2]
                if prev_ma12 and float(prev_ma12) > 0:
                    ma12_5 = prev_ma12
                    print(f"  ⚠️ {ticker} MA12 is 0 or invalid. Using Prev: {ma12_5:.2f}")
            
            # [Ver 8.0.5] Inject MA12 to Results for persistent UI display
            results[t]['ma12'] = float(ma12_5) if ma12_5 and float(ma12_5) > 0 else 0
            
            # 30m Indicators
            ma10_30 = df_30['ma10'].iloc[-1]
            ma30_30 = df_30['ma30'].iloc[-1]
            prev_ma10_30 = df_30['ma10'].iloc[-2]
            prev_ma30_30 = df_30['ma30'].iloc[-2]
            
            # --- Logic Checking ---
            
            # [Ver 6.5.8] BBI (박스권 탈출 지수) 계산 - 신호 필터링용
            bbi_result = calculate_bbi(df_30)
            bbi_score = bbi_result['bbi']
            bbi_status = bbi_result['status']
            print(f"  📊 {ticker} BBI: {bbi_score} ({bbi_status})")
            
            # BBI 기반 신호 필터링 여부 결정
            # BBI < -3: 심각한 박스권 → 신호 사운드/SMS 억제 (기존 0에서 완화)
            # BBI >= -3: 약한 횡보는 허용
            bbi_filter_active = bbi_score < -3
            

            
            # [Ver 5.8.3] Independent Signal Processing
            # Each signal checks and updates INDEPENDENTLY
            sounds_to_play = set()
            
            # --- BUY SIDE ---
            buy_record = get_v2_buy_status(ticker)
            # Condition checks (calculated once, used multiple times)
            is_5m_gc_cross = (prev_ma10_5 <= prev_ma30_5) and (ma10_5 > ma30_5)
            is_5m_trend_up = (ma10_5 > ma30_5)
            is_30m_gc = (prev_ma10_30 <= prev_ma30_30) and (ma10_30 > ma30_30)
            is_30m_trend_up = (ma10_30 > ma30_30)

            # [DEBUG] Signal Logic Trace
            print(f"  🔍 {ticker} 5m: MA10={ma10_5:.4f}, MA30={ma30_5:.4f} (Diff: {ma10_5-ma30_5:.4f}) {'[UP]' if is_5m_trend_up else '[DOWN]'}")
            print(f"  🔍 {ticker} 30m: MA10={ma10_30:.4f}, MA30={ma30_30:.4f} (Diff: {ma10_30-ma30_30:.4f}) {'[UP]' if is_30m_trend_up else '[DOWN]'}")
            
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
            
            # ═══════════════════════════════════════════════════════════════════
            # [Ver 5.8.4] SOXL/SOXS 매수/매도 신호 시스템
            # ═══════════════════════════════════════════════════════════════════
            #
            # ┌─────────────────────────────────────────────────────────────────┐
            # │  매수 신호 (BUY SIGNALS) - 진입 조건                              │
            # ├─────────────────────────────────────────────────────────────────┤
            # │  1차: 5분봉 골든크로스 (MA10 > MA30)                              │
            # │       → 단기 상승 추세 시작                                       │
            # │                                                                  │
            # │  2차: 5분봉 가격 지지 (Price > MA12)                             │
            # │       → [Ver 7.6] 트렌드 지지선 확보 (Simple Support)            │
            # │                                                                  │
            # │  3차: 30분봉 골든크로스 (MA10 > MA30)                             │
            # │       → 중기 상승 추세 확정                                       │
            # │                                                                  │
            # │  최종: 1차 + 2차 + 3차 모두 충족 시 진입 완료                      │
            # └─────────────────────────────────────────────────────────────────┘
            #
            # ┌─────────────────────────────────────────────────────────────────┐
            # │  매도 신호 (SELL SIGNALS) - 청산 조건                             │
            # ├─────────────────────────────────────────────────────────────────┤
            # │  1차: 5분봉 데드크로스 (MA10 < MA30)                              │
            # │       → 단기 조정 신호                                           │
            # │                                                                  │
            # │  2차: Trailing Stop (-1.5% from High)                            │
            # │       → 자동: 당일 고점 대비 -1.5% 하락 시                        │
            # │       → 수동: 사용자 지정가 이탈 시                               │
            # │                                                                  │
            # │  3차: 30분봉 데드크로스 (MA10 < MA30)                             │
            # │       → 추세 전환 확정, 청산 권고                                 │
            # └─────────────────────────────────────────────────────────────────┘
            # ═══════════════════════════════════════════════════════════════════

            # Check if we are in HOLDING mode (already bought)
            # [Ver 7.2.8] Hybrid Trading: Auto Final OR Manual Real Buy = Holding
            is_holding = buy_record and (buy_record.get('final_buy_yn') == 'Y' or buy_record.get('real_buy_yn') == 'Y')
            
            # ────────────────────────────────────────────────────────────────
            # SIGNAL 1: 5분봉 Golden Cross (자동 + 수동)
            # [Ver 6.5.2] Real-Time Update: Check even if holding
            # ────────────────────────────────────────────────────────────────
            if buy_record:
                manage_id = buy_record.get('manage_id', 'UNKNOWN')
                sig1_manual = buy_record.get('is_manual_buy1') == 'Y'
                
                if is_5m_trend_up:
                    if buy_record['buy_sig1_yn'] == 'N':
                        if save_v2_buy_signal(ticker, 'sig1', curr_price):
                            msg_type = "5분봉 GC" if is_5m_gc_cross else "5분봉 상승추세"
                            print(f"🚀 {ticker} Signal 1 ON ({msg_type})")
                            log_history(manage_id, ticker, "1차매수신호", msg_type, curr_price)
                            sounds_to_play.add(('buy1', ticker))
                else:
                    if buy_record['buy_sig1_yn'] == 'Y':
                        try:
                            # [Ver 7.4.2] Use System Save to turn OFF Score, Ignore Manual Flag
                            save_v2_buy_signal(ticker, 'sig1', 0, 'N')
                            print(f"📉 {ticker} Signal 1 OFF (5m trend lost)")
                            
                            # [Cascade Reset] If Step 1 fails, Step 2 is INDEPENDENT (User Req Ver 7.2)
                            # Only Final is cascade removed if it depends on Sig 1 (Conceptually Final needs all 3)
                            # But if Sig 2 is independent, maybe Final should be too?
                            # Guide says: "Final: 1+2+3". If 1 is off, Final is technically invalid.
                            # But user only asked for Sig 2 independence. Let's keep Final cascade for safety?
                            # User: "1차 신호가 해제 되면 바로 2차 신호도 해제가 되니까 .. 2차 신호 발생 가격이 유지 되면 신호도 유지"
                            # Does not explicitly mention Final. But usually Final = Strong Buy.
                            # If 1 is off (Trend broken), Final might be risky. Let's start with Sig 2 independence only.
                            
                            # if buy_record['buy_sig2_yn'] == 'Y':
                            #     manual_update_signal(ticker, 'buy2', 0, 'N')
                            
                            if buy_record['final_buy_yn'] == 'Y':
                                manual_update_signal(ticker, 'final', 0, 'N')
                                print(f"📉 {ticker} Final Signal REMOVED (Cascade from Sig1)")
                        except: pass
            
            # ────────────────────────────────────────────────────────────────
            # SIGNAL 2: 5분봉 MA12 지지 (Price > MA12)
            # [Ver 7.6] Simple MA12 Support Filter
            # ────────────────────────────────────────────────────────────────
            if buy_record:
                sig2_manual = buy_record.get('is_manual_buy2') == 'Y'
                
                # 수동: 사용자 지정가 돌파
                custom_target = buy_record.get('target_box_price')
                if custom_target and float(custom_target) > 0:
                    is_sig2_met = (curr_price >= float(custom_target))
                    sig2_reason = f"지정가 돌파 (${custom_target})"
                else:
                    # 자동: [New Standard] Price > 5m MA12
                    # Note: ma12 is calculated above
                    # [Ver 8.0.1] 0 Value Protection (Data Error Fix)
                    is_sig2_met = (curr_price > ma12_5 and ma12_5 > 0 and curr_price > 0)
                    sig2_reason = f"상승지속 1h (${ma12_5:.2f})"
                
                # Logic
                if is_sig2_met:
                    # Condition Met
                    if buy_record['buy_sig2_yn'] == 'N':
                        # Entry Attempt: Must have Sig 1 active to START Signal 2 (Sequential)
                        # User wants Sig 2 independent? Request says "Price > MA12" only.
                        # But Lab says "Sig 2 = Sig 1".
                        # Dashboard context: usually sequential or weighted.
                        # Guide V2.1 says "Price > MA12".
                        # Let's allow it if Sig 1 is ON (Sequential usually safer for scoring structure),
                        # OR treat as independent bonus?
                        # User request: "2차 매수신호 수정 : 현재가가 ... 위에 있으면 신호 발생"
                        # Doesn't explicitly say "regardless of 1st signal".
                        # But to be score-additive, it should probably be independent or semi-independent.
                        # Existing code had "Requires Sig 1".
                        # Let's keep "Requires Sig 1" for ENTRY to keep the "Tower" concept (Base -> Mid -> Top).
                        # But EXIT (Off) is strictly condition-based.
                        
                        if buy_record['buy_sig1_yn'] == 'Y':
                             if save_v2_buy_signal(ticker, 'sig2', curr_price):
                                 print(f"🚀 {ticker} Signal 2 ON ({sig2_reason})")
                                 log_history(manage_id, ticker, "2차매수신호", sig2_reason, curr_price)
                                 sounds_to_play.add(('buy2', ticker))
                else:
                    # Condition Lost (Price <= MA12)
                    if buy_record['buy_sig2_yn'] == 'Y':
                        try:
                            # [Ver 8.0.4] Fix: Save actual MA12 value instead of 0 for UI reference
                            save_v2_buy_signal(ticker, 'sig2', ma12_5 if ma12_5 > 0 else 0, 'N')
                            print(f"📉 {ticker} Signal 2 OFF (Price <= MA12)")
                        except: pass
            
            # ────────────────────────────────────────────────────────────────
            # SIGNAL 3: 30분봉 Golden Cross (자동 + 수동)
            # ────────────────────────────────────────────────────────────────
            if buy_record:
                sig3_manual = buy_record.get('is_manual_buy3') == 'Y'
                
                if is_30m_trend_up:
                    if buy_record['buy_sig3_yn'] == 'N':
                        if save_v2_buy_signal(ticker, 'sig3', curr_price):
                            msg_type = "30분봉 GC" if is_30m_gc else "30분봉 상승추세"
                            print(f"🚀 {ticker} Signal 3 ON ({msg_type})")
                            log_history(manage_id, ticker, "3차매수신호", msg_type, curr_price)
                            sounds_to_play.add(('buy3', ticker))
                else:
                    if buy_record['buy_sig3_yn'] == 'Y':
                        try:
                            save_v2_buy_signal(ticker, 'sig3', 0, 'N')
                            print(f"📉 {ticker} Signal 3 OFF (30m trend lost)")
                            # If Step 3 lost, Final also blocked? Maybe not strictly sequential but Final requires all 3.
                            if buy_record['final_buy_yn'] == 'Y':
                                manual_update_signal(ticker, 'final', 0, 'N')
                        except: pass
            
            # ────────────────────────────────────────────────────────────────
            # FINAL BUY: 최종 진입 확정
            # ────────────────────────────────────────────────────────────────
            if buy_record:
                updated_buy = get_v2_buy_status(ticker)
                if updated_buy:
                    all_met = (updated_buy['buy_sig1_yn'] == 'Y' and 
                               updated_buy['buy_sig2_yn'] == 'Y' and 
                               updated_buy['buy_sig3_yn'] == 'Y')
                    
                    if all_met and updated_buy['final_buy_yn'] == 'N':
                        if save_v2_buy_signal(ticker, 'final', curr_price):
                            print(f"🎯 {ticker} FINAL BUY! All conditions met.")
                            log_history(manage_id, ticker, "최종진입완료", "Triple Filter Complete", curr_price)
                            sounds_to_play.add(('final_buy', ticker))
                    elif not all_met and updated_buy['final_buy_yn'] == 'Y':
                        # Auto Remove Final if any condition fails
                        try:
                             from db import manual_update_signal
                             manual_update_signal(ticker, 'final', 0, 'N')
                             print(f"📉 {ticker} Final Signal REMOVED (Conditions not met)")
                        except: pass
            
            # ────────────────────────────────────────────────────────────────
            # SMS 발송 (우선순위: final > 3차 > 2차 > 1차)
            # [Ver 6.5.8] BBI 필터: 박스권(BBI<0)일 때는 SMS 발송 억제
            # ────────────────────────────────────────────────────────────────
            if sounds_to_play:
                # [Ver 6.5.9] BBI Filter Optim: -3 미만일 때만 SMS 차단
                if not bbi_filter_active:
                    sms_time = get_current_time_str_sms()
                    
                    # BBI가 0 미만이지만 -3 이상인 경우 (Weak) → 메시지에 표기
                    bbi_note = f" (BBI:{bbi_score})"
                    if bbi_score < 0:
                        bbi_note = f" (Low Vol/BBI:{bbi_score})"

                    if ('final_buy', ticker) in sounds_to_play:
                        send_sms(ticker, "최종매수(V2)", curr_price, sms_time, f"트리플필터완성{bbi_note}")
                    elif ('buy3', ticker) in sounds_to_play:
                        send_sms(ticker, "3차매수(30분봉)", curr_price, sms_time, f"30분봉 추세확정{bbi_note}")
                    elif ('buy2', ticker) in sounds_to_play:
                        send_sms(ticker, "2차매수(+1%)", curr_price, sms_time, f"상승 지속 확인{bbi_note}")
                    elif ('buy1', ticker) in sounds_to_play:
                        send_sms(ticker, "1차매수(5분봉)", curr_price, sms_time, f"5분봉 골든크로스{bbi_note}")
                
                else:
                    # Filter Active (BBI < -3)
                    print(f"  🔇 {ticker} SMS 억제 (심한 박스권: BBI={bbi_score} < -3)")

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

            # [Ver 6.5.6] Orphan Sell Signal Cleanup: 보유 중이 아닌데 sell 신호가 있으면 정리
            if sell_record and not is_holding:
                try:
                    from db import manual_update_signal
                    if sell_record.get('sell_sig1_yn') == 'Y':
                        manual_update_signal(ticker, 'sell1', 0, 'N')
                    if sell_record.get('sell_sig2_yn') == 'Y':
                        manual_update_signal(ticker, 'sell2', 0, 'N')
                    if sell_record.get('sell_sig3_yn') == 'Y':
                        manual_update_signal(ticker, 'sell3', 0, 'N')
                    print(f"🧹 {ticker} Orphan sell signals cleaned (not holding)")
                except Exception as e:
                    print(f"⚠️ {ticker} Orphan cleanup error: {e}")

            # Only process sell signals if in HOLDING mode
            if sell_record and is_holding:
                manage_id = sell_record.get('manage_id', 'UNKNOWN')
                
                # Calculate conditions once
                is_5m_dc = (prev_ma10_5 >= prev_ma30_5) and (ma10_5 < ma30_5)
                is_5m_trend_down = (ma10_5 < ma30_5)
                
                # Day High calculation (Ensure Monotonic Increase)
                # Start with max of Current Price and DB Stored High
                db_day_high = float(sell_record.get('day_high_price') or 0)
                day_high = max(curr_price, db_day_high)
                
                if df_5 is not None and not df_5.empty:
                    recent_high = df_5['High'].tail(80).max()
                    day_high = max(day_high, float(recent_high))
                
                trailing_stop_price = day_high * 0.985
                is_trailing_stop = (curr_price <= trailing_stop_price)
                
                # Save Day High to DB (Only update if increased)
                if day_high > db_day_high:
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
                        # [Ver 7.2.9] Auto Trigger -> is_manual='N'
                        manual_update_signal(ticker, 'sell1', curr_price, 'Y', is_manual_override='N')
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
                    # [Ver 6.5.6] 실시간 업데이트: 수동 플래그 무시하고 조건 미충족 시 OFF
                    if sell_record['sell_sig1_yn'] == 'Y':
                        try:
                            from db import manual_update_signal
                            # Auto Off -> is_manual='N'
                            manual_update_signal(ticker, 'sell1', 0, 'N', is_manual_override='N')
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
                        # [Ver 7.2.9] Auto Trigger (Trailing Stop) -> is_manual='N'
                        manual_update_signal(ticker, 'sell2', curr_price, 'Y', is_manual_override='N')
                        print(f"🎯 {ticker} Sell Signal 2 ON ({sig2_reason})")
                        log_history(manage_id, ticker, "2차청산신호", sig2_reason, curr_price)
                        sell_sounds.add(('sell2', ticker))
                else:
                    # [Ver 6.5.6] 실시간 업데이트: 수동 플래그 무시하고 조건 미충족 시 OFF
                    if sell_record['sell_sig2_yn'] == 'Y':
                        try:
                            from db import manual_update_signal
                            manual_update_signal(ticker, 'sell2', 0, 'N', is_manual_override='N')
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
                # [Ver 6.5.8] BBI 필터: 박스권일 때 매도 신호도 억제 (단, 보유 중일 때는 리스크 관리 위해 발송)
                if sell_sounds:
                    sms_time = get_current_time_str_sms()
                    if ('sell3', ticker) in sell_sounds:
                        send_sms(ticker, "3차청산", curr_price, sms_time, f"최종 목표가 도달 (BBI:{bbi_score})")
                    elif ('sell2', ticker) in sell_sounds:
                        send_sms(ticker, "2차청산", curr_price, sms_time, f"손절/이익실현 (BBI:{bbi_score})")
                    elif ('sell1', ticker) in sell_sounds:
                        send_sms(ticker, "1차청산", curr_price, sms_time, f"5분봉 하락추세 (BBI:{bbi_score})")
                
                # ────────────────────────────────────────────────────────────────
                # Price Level Alerts (사용자 지정가 알림)
                # ────────────────────────────────────────────────────────────────
                # BUY: 현재가 >= 지정가 → triggered='Y' (상승 돌파)
                # SELL: 현재가 <= 지정가 → triggered='Y' (하락 이탈)
                # 조건 해제 시 → triggered='N' (자동 리셋)
                # [Ver 5.9.2] 항상 market_indices에서 현재가 조회 (장중/휴장 무관)
                # ────────────────────────────────────────────────────────────────
                try:
                    from db import get_price_levels, set_price_level_triggered, reset_price_level_triggered_only, get_connection
                    
                    # market_indices에서 현재가 조회
                    conn = get_connection()
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT current_price FROM market_indices WHERE ticker=%s", (ticker,))
                        row = cursor.fetchone()
                        alert_price = float(row['current_price']) if row and row['current_price'] else 0
                    conn.close()
                    
                    if alert_price <= 0:
                        print(f"⚠️ {ticker} Alert Skip: No valid price in market_indices")
                    else:
                        active_levels = get_price_levels(ticker)
                        
                        for lvl in active_levels:
                            if lvl['is_active'] != 'Y':
                                continue
                                
                            l_type = lvl['level_type']
                            l_price = float(lvl['price'])
                            is_triggered = lvl['triggered'] == 'Y'
                            
                            # 조건 충족 여부 확인
                            condition_met = False
                            if l_type == 'BUY' and l_price > 0:
                                condition_met = (alert_price >= l_price)
                            elif l_type == 'SELL' and l_price > 0:
                                condition_met = (alert_price <= l_price)
                            
                            # 조건 충족 → trigger ON
                            if condition_met and not is_triggered:
                                set_price_level_triggered(ticker, l_type, lvl['stage'])
                                print(f"🔔 {ticker} Alert ON: {l_type} #{lvl['stage']} @ ${l_price} (curr: ${alert_price})")
                            
                            # 조건 해제 → trigger OFF (자동 리셋)
                            elif not condition_met and is_triggered:
                                reset_price_level_triggered_only(ticker, l_type, lvl['stage'])
                                print(f"🔕 {ticker} Alert OFF: {l_type} #{lvl['stage']} (조건 해제, curr: ${alert_price})")
                            
                except Exception as e:
                    print(f"Price Alert Error: {e}")


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
        # Fetch recent candles from KIS
        candles = kis_client.get_minute_candles(ticker, interval_min=interval_min)
        if not candles: 
            print(f"    ⚠️ Stitch: No KIS candles for {ticker} (Interval {interval_min}m)")
            return yf_df
        
        print(f"    🧵 Stitch {ticker} ({interval_min}m): Fetched {len(candles)} candles. Last: {candles[0]['khms']} (KST)")
        
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
