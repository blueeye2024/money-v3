
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
import datetime
import pandas as pd
import numpy as np
import requests
import json
import uuid
import time
from db import get_connection
from kis_api_v2 import kis_client
from analysis import calculate_tech_indicators, calculate_holding_score, check_triple_filter, calculate_bbi, get_cross_history

router = APIRouter(prefix="/api/lab", tags=["lab"])

# --- Models ---
class SimRequest(BaseModel):
    ticker: str
    date: str # YYYY-MM-DD

# --- Helpers ---

def get_kst_time_range(target_date_str):
    """
    Returns (start_dt, end_dt) in datetime objects
    Target: 09:00 KST of Date ~ 09:00 KST of Date+1
    """
    base_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
    # KST is target
    # But usually we work in "Native" time for KIS (Local Exchange Time or KST?)
    # KIS returns data with KST dates usually.
    # Let's assume KST for now.
    start_dt = base_date.replace(hour=9, minute=0, second=0)
    end_dt = start_dt + datetime.timedelta(hours=24) # Next day 9am
    return start_dt, end_dt

def fetch_historical_candles_paginated(ticker, start_dt, end_dt):
    """
    Fetch enough 5m candles to cover start_dt ~ end_dt.
    We fetch backwards from 'NOW' (or recent file) using KIS API.
    Since KIS 'inquire-time-itemchartprice' is 'recent first', we paginate using NEXT key.
    """
    candles = []
    next_key = ""
    
    # Safety limit
    max_pages = 50 
    
    # We need to fetch until the earliest candle is BEFORE start_dt (minus buffer)
    # Let's aim for start_dt - 10 hours buffer for moving averages
    target_stop_dt = start_dt - datetime.timedelta(hours=20)
    
    token = kis_client.ensure_fresh_token()
    access_token = kis_client.access_token
    
    exchange = "NAS" # Default, logic from kis_api can verify
    # Use internal map logic if needed, or just default. 
    # Calling kis_client.get_minute_candles wrapper handles exchange daytime logic?
    # But we want raw pagination.
    # Let's borrow exchange logic
    from kis_api_v2 import get_exchange_code
    exchange = get_exchange_code(ticker)
    
    # We ignore "Daytime" logic here because we are fetching HISTORY regardless of time of day?
    # KIS API usually works with specific exchange codes.
    # For backtest, standard NAS/NYS is safer.
    
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": kis_client.APP_KEY,
        "appsecret": kis_client.APP_SECRET,
        "tr_id": "HHDFS76950200"
    }
    
    print(f"  [LAB] Fetching history for {ticker} ({exchange}) since {target_stop_dt}...")
    
    for i in range(max_pages):
        params = {
            "AUTH": "", "EXCD": exchange, "SYMB": ticker,
            "NMIN": "5", "PINC": "1", "NEXT": next_key, "NREC": "120", "KEYB": ""
        }
        
        try:
            res = requests.get(f"{kis_client.URL_BASE}/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice", headers=headers, params=params, timeout=5.0)
            if res.status_code == 200:
                data = res.json()
                if data['rt_cd'] == '0':
                    batch = data['output2']
                    if not batch: break
                    
                    # Process timestamps to check if we reached limit
                    # kymd: YYYYMMDD, khms: HHMMSS
                    last_c = batch[-1]
                    last_dt_str = f"{last_c['kymd']}{last_c['khms']}"
                    last_dt = datetime.datetime.strptime(last_dt_str, "%Y%m%d%H%M%S")
                    
                    candles.extend(batch)
                    
                    # print(f"    Page {i}: Got {len(batch)} candles. Oldest: {last_dt}")
                    
                    if last_dt < target_stop_dt:
                        # Reached far enough
                        break
                        
                    # Get Next Key? KIS API returns headers or output1?
                    # Wait, KIS Foreign Stock Minute API usually doesn't return NEXT key in header?
                    # It puts it in output1? No.
                    # Usually for Minute chart, we might not have 'NEXT' key support in this specific TR?
                    # HHDFS76950200 doc says: "NEXT" : "Next Key". 
                    # Where is it returned? It is often in header 'tr_cont_key' or body?
                    # Let's check headers.
                    tr_cont = res.headers.get('tr_cont')
                    tr_cont_key = res.headers.get('tr_cont_key')
                    
                    # print(f"    Headers: tr_cont={tr_cont} key={tr_cont_key}")
                    
                    if tr_cont == 'M' or tr_cont == 'D': # M/D means More Data
                        next_key = tr_cont_key
                    else:
                        break # No more data
                else:
                    print(f"API Error: {data['msg1']}")
                    break
            else:
                break
        except Exception as e:
            print(f"Fetch Error: {e}")
            break
            
        time.sleep(0.1)
        
    # Convert to DataFrame
    raw_data = []
    for c in candles:
        # KST assumtion from KIS
        dt = datetime.datetime.strptime(f"{c['kymd']}{c['khms']}", "%Y%m%d%H%M%S")
        raw_data.append({
            'time': dt,
            'open': float(c['open']),
            'high': float(c['high']),
            'low': float(c['low']),
            'close': float(c['last']),
            'volume': float(c['vol'])
        })
        
    df = pd.DataFrame(raw_data)
    if df.empty: return df
    
    df = df.sort_values('time').reset_index(drop=True)
    return df

def resample_30m(df_5m):
    """Upsample 5m to 30m"""
    if df_5m.empty: return pd.DataFrame()
    
    df = df_5m.set_index('time').copy()
    
    # Resample logic
    # 30T = 30 minutes
    # OHLCV aggregation
    df_30 = df.resample('30min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    df_30 = df_30.reset_index()
    return df_30

# --- Core Task ---

def run_simulation(sim_id: str, ticker: str, target_date: str):
    conn = get_connection()
    try:
        start_dt, end_dt = get_kst_time_range(target_date)
        print(f"🚀 [LAB] Sim {sim_id}: Fetching Data for {ticker} ({start_dt} ~ {end_dt})")
        
        # 1. Fetch
        df_5m_all = fetch_historical_candles_paginated(ticker, start_dt, end_dt)
        if df_5m_all.empty:
            print("❌ No data found.")
            return

        print(f"  Data Loaded: {len(df_5m_all)} candles. Range: {df_5m_all.iloc[0]['time']} ~ {df_5m_all.iloc[-1]['time']}")
        
        # 2. Iterate (Replay)
        # We only care about scoring candles that fall inside [start_dt, end_dt]
        # But we need previous data for indicators.
        
        mask = (df_5m_all['time'] >= start_dt) & (df_5m_all['time'] <= end_dt)
        target_indices = df_5m_all[mask].index
        
        results_to_save = []
        
        for idx in target_indices:
            # Slice: History up to this candle
            # Use at least 200 candles if available for MA calculation
            slice_start = max(0, idx - 300) 
            snapshot_5m = df_5m_all.iloc[slice_start : idx+1].copy()
            
            current_time = snapshot_5m.iloc[-1]['time']
            current_price = snapshot_5m.iloc[-1]['close']
            
            # --- Analysis Logic ---
            
            # A. Calc Indicators (5m)
            tech_5m = calculate_tech_indicators(snapshot_5m)
            
            # B. Calc 30m Indicators
            # Resample strictly from the snapshot
            snapshot_30m = resample_30m(snapshot_5m)
            # tech_30m = calculate_tech_indicators(snapshot_30m) # Used inside check_triple_filter?
            
            # C. Triple Filter V2
            # check_triple_filter expects DICT of DataFrames? No, params are data_30m, data_5m
            # But check_triple_filter function in analysis.py:
            # def check_triple_filter(ticker, data_30m, data_5m):
            # It expects data_30m and data_5m to be DICTIONARIES of dataframes keyed by ticker: { 'SOXL': df }
            # So we wrap them.
            
            d30 = {ticker: snapshot_30m}
            d5 = {ticker: snapshot_5m}
            
            # Also it fetches 'current_price' inside?
            # It uses `data_5m[ticker].iloc[-1]['close']`
            
            v2_res = check_triple_filter(ticker, d30, d5)
            
            # D. Holding Score V4
            # calculate_holding_score(res, tech, v2_buy, v2_sell, bbi_score)
            
            # V2 Buy/Sell Status extraction
            # v2_res contains 'final', 'step1', 'metrics' etc.
            # We need to simulate the 'v2_buy' status DB object?
            # calculate_holding_score uses v2_buy_info dict: { 'buy_sig1_yn': 'Y', ... }
            # v2_res returns the CURRENT status.
            # In live system, these are cumulative/persistent in DB.
            # In Backtest, since we are replay-ing each candle, the 'current status' IS the status of that moment.
            # So if v2_res['step1'] is True, buy_sig1_yn is Y.
            
            # construct mock v2_buy/sell
            mock_v2_buy = {
                'buy_sig1_yn': 'Y' if v2_res.get('step1') else 'N',
                'buy_sig2_yn': 'Y' if v2_res.get('step2') else 'N',
                'buy_sig3_yn': 'Y' if v2_res.get('step3') else 'N',
            }
            # For Sell, V2 logic returns 'sell_signal' flags?
            # check_triple_filter returns 'sell_step1', 'sell_step2', 'sell_step3'?
            # Let's check keys in v2_res. It usually has 'steps': [T, F, F] for buy?
            # Actually check_triple_filter implementation details:
            # It returns: { 'final': bool, 'step1': bool, ..., 'sell_step1': bool ... }
            
            mock_v2_sell = {
                'sell_sig1_yn': 'Y' if v2_res.get('sell_step1') else 'N',
                'sell_sig2_yn': 'Y' if v2_res.get('sell_step2') else 'N', # Trailing Stop logic might be complex in backtest
                'sell_sig3_yn': 'Y' if v2_res.get('sell_step3') else 'N',
            }
            
            # BBI
            bbi_val = 0
            if not snapshot_30m.empty:
                bbi_res = calculate_bbi(snapshot_30m)
                bbi_val = bbi_res.get('bbi', 0)
                
            # Score
            score_data = calculate_holding_score(
                v2_res, 
                tech_5m, 
                mock_v2_buy, 
                mock_v2_sell, 
                bbi_score=bbi_val
            )
            
            # Save Row
            bd = score_data.get('breakdown', {})
            
            # Identify active signal step (text)
            sig_text = []
            if mock_v2_buy['buy_sig3_yn'] == 'Y': sig_text.append("Buy L3")
            elif mock_v2_buy['buy_sig2_yn'] == 'Y': sig_text.append("Buy L2")
            elif mock_v2_buy['buy_sig1_yn'] == 'Y': sig_text.append("Buy L1")
            
            if mock_v2_sell['sell_sig3_yn'] == 'Y': sig_text.append("Sell L3")
            elif mock_v2_sell['sell_sig1_yn'] == 'Y': sig_text.append("Sell L1")
            
            
            results_to_save.append((
                sim_id,
                ticker,
                current_time.strftime('%Y-%m-%d %H:%M:%S'),
                current_price,
                v2_res.get('daily_change', 0),
                score_data.get('score', 0),
                bd.get('cheongan', 0),
                bd.get('rsi', 0),
                bd.get('macd', 0),
                bd.get('vol', 0),
                bd.get('atr', 0),
                bd.get('bbi', 0),
                ", ".join(sig_text)
            ))
            
        print(f"  Simulation Completed. Saving {len(results_to_save)} rows...")
        
        # Batch Insert
        if results_to_save:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO backtest_results 
                    (simulation_id, ticker, candle_time, price, change_pct, total_score, 
                     cheongan_score, rsi, macd, vol_ratio, atr, bbi, signal_step)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.executemany(sql, results_to_save)
            conn.commit()
            print("✅ DB Save Success")
            
    except Exception as e:
        print(f"❌ Sim Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


@router.post("/simulate")
def request_simulation(req: SimRequest, background_tasks: BackgroundTasks):
    sim_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(run_simulation, sim_id, req.ticker, req.date)
    return {"status": "success", "message": "Simulation started", "simulation_id": sim_id}

@router.get("/results/{sim_id}")
def get_results(sim_id: str):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM backtest_results WHERE simulation_id = %s ORDER BY candle_time ASC"
            cursor.execute(sql, (sim_id,))
            rows = cursor.fetchall()
            return {"status": "success", "data": rows}
    finally:
        conn.close()
