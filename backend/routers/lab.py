
from fastapi import APIRouter, File, UploadFile, HTTPException
import pandas as pd
import io
import datetime
from db_lab import init_lab_tables, bulk_insert_lab_data
from analysis import calculate_tech_indicators, calculate_holding_score, calculate_market_energy, calculate_bbi, check_triple_filter

def clean_score(val):
    if pd.isna(val): return 0
    return int(val)

router = APIRouter(prefix="/api/lab", tags=["lab"])

# Ensure tables exist on module load (or first call)
try:
    init_lab_tables()
except:
    pass

@router.post("/upload")
async def upload_lab_data(file: UploadFile = File(...), period: str = "30m", ticker: str = "SOXL"):
    """
    Excel Upload for Lab Data.
    period: '30m' or '5m'
    ticker: Target ticker if not in file (default SOXL)
    """
    if period not in ['30m', '5m']:
        raise HTTPException(status_code=400, detail="Invalid period. Use '30m' or '5m'.")

    # Read File
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")

    # Expected Columns Mapping (User Specific)
    col_map = {
        '일자': 'Date', '시간': 'Time', 
        '시가': 'Open', '고가': 'High', '저가': 'Low', '종가': 'Close', 
        '거래량': 'Volume',
        '10': 'MA10', # Specific User Request
        '30': 'MA30', # Specific User Request
        '등락률': 'ChangePct'
    }
    
    df.rename(columns=col_map, inplace=True)
    
    # Check Required
    # Note: Ticker is properly NOT required in file now, we use param.
    required = ['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing = [c for c in required if c not in df.columns]
    
    if missing:
         raise HTTPException(status_code=400, detail=f"Missing required columns: {missing}")

    # Process Data
    data_to_insert = []
    processed_count = 0
    
    target_ticker = ticker.strip().upper()
    
    for _, row in df.iterrows():
        try:
            # 1. Ticker (Use param if col missing)
            row_ticker = row.get('Ticker', target_ticker)
            if pd.isna(row_ticker): row_ticker = target_ticker
            
            # 2. DateTime
            d_val = row['Date']
            t_val = row['Time']
            
            if pd.isna(d_val) or pd.isna(t_val): continue 
            
            d_str = ""
            # Handle Date
            if isinstance(d_val, pd.Timestamp):
                 d_str = d_val.strftime("%Y-%m-%d")
            elif isinstance(d_val, datetime.datetime):
                d_str = d_val.strftime("%Y-%m-%d")
            else:
                d_str = str(d_val).split(' ')[0].replace('/', '-')
            
            # Handle Time
            t_str = ""
            if isinstance(t_val, pd.Timestamp):
                 t_str = t_val.strftime("%H:%M:%S")
            elif isinstance(t_val, datetime.time):
                t_str = t_val.strftime("%H:%M:%S")
            else:
                t_str = str(t_val).strip()
                # Fix "HH:MM" -> "HH:MM:00"
                if len(t_str) == 5 and t_str.count(':') == 1:
                    t_str += ":00"
                
            # Combine
            full_dt_str = f"{d_str} {t_str}"
            try:
                candle_time = datetime.datetime.strptime(full_dt_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                 print(f"Skipping Bad Date Format: {full_dt_str}")
                 continue
            
            # 3. Values
            o = float(row['Open'])
            h = float(row['High'])
            l = float(row['Low'])
            c = float(row['Close'])
            v = int(row['Volume'])
            ma10 = float(row.get('MA10', 0) or 0)
            ma30 = float(row.get('MA30', 0) or 0)
            
            # Change Pct (Optional / Calc)
            chg = 0.0
            if 'ChangePct' in row:
                chg = float(row['ChangePct'] or 0)
            
            data_to_insert.append((row_ticker, candle_time, o, h, l, c, v, ma10, ma30, chg))
            processed_count += 1
            
        except Exception as row_e:
            print(f"Skipping Bad Row: {row} -> {row_e}")
            continue

    # Insert to DB
    table_name = "lab_data_30m" if period == "30m" else "lab_data_5m"
    try:
        inserted = bulk_insert_lab_data(table_name, data_to_insert)
        return {
            "status": "success", 
            "message": f"Processed {processed_count} rows. Inserted/Updated {inserted} records into {table_name}.",
            "total_rows": len(df)
        }
    except Exception as db_e:
        raise HTTPException(status_code=500, detail=f"DB Error: {str(db_e)}")


@router.get("/config")
def get_lab_config():
    """Get Lab Buy/Sell Thresholds"""
    from db import get_global_config
    return {
        "lab_buy_score": get_global_config("lab_buy_score", 70),
        "lab_sell_score": get_global_config("lab_sell_score", 50)
    }

from pydantic import BaseModel
class LabConfig(BaseModel):
    lab_buy_score: int
    lab_sell_score: int

@router.post("/config")
def set_lab_config(config: LabConfig):
    """Set Lab Buy/Sell Thresholds"""
    from db import set_global_config
    try:
        set_global_config("lab_buy_score", config.lab_buy_score)
        set_global_config("lab_sell_score", config.lab_sell_score)
        return {"status": "success", "message": "Thresholds saved."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{period}")
def get_lab_data(period: str, page: int = 1, limit: int = 50, ticker: str = None, date_from: str = None, date_to: str = None, status: str = "ALL"):
    """
    View loaded data with Pagination & Filtering.
    """
    from db import get_connection
    table = "lab_data_30m" if period == "30m" else "lab_data_5m"
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Base Query
            where_clauses = ["1=1"]
            params = []
            
            if ticker and ticker != "ALL":
                where_clauses.append("ticker = %s")
                params.append(ticker)
                
            if date_from:
                where_clauses.append("candle_time >= %s")
                params.append(date_from)
            
            if date_to:
                where_clauses.append("candle_time <= %s")
                params.append(date_to + " 23:59:59") # End of day

            # [Status Filter]
            if status == "COMPLETE":
                where_clauses.append("total_score != 0")
            elif status == "INCOMPLETE":
                where_clauses.append("total_score = 0")
                
            where_sql = " AND ".join(where_clauses)
            
            # Count Total
            count_sql = f"SELECT COUNT(*) as cnt FROM {table} WHERE {where_sql}"
            cursor.execute(count_sql, tuple(params))
            total_rows = cursor.fetchone()['cnt']
            
            # Fetch Page
            offset = (page - 1) * limit
            sql = f"SELECT * FROM {table} WHERE {where_sql} ORDER BY candle_time DESC LIMIT %s OFFSET %s"
            cursor.execute(sql, tuple(params + [limit, offset]))
            rows = cursor.fetchall()
            
            return {
                "status": "success", 
                "data": rows, 
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_rows,
                    "total_pages": (total_rows + limit - 1) // limit
                }
            }
    finally:
        conn.close()

@router.delete("/data/{period}")
def delete_lab_data(period: str, ids: str): # ids="1,2,3"
    """
    Bulk Delete by IDs.
    """
    from db import get_connection
    table = "lab_data_30m" if period == "30m" else "lab_data_5m"
    
    if not ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
        
    id_list = [int(x) for x in ids.split(',')]
    if not id_list:
         return {"status": "error", "message": "No valid IDs"}

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            format_strings = ','.join(['%s'] * len(id_list))
            sql = f"DELETE FROM {table} WHERE id IN ({format_strings})"
            cursor.execute(sql, tuple(id_list))
            deleted = cursor.rowcount
            conn.commit()
            return {"status": "success", "message": f"Deleted {deleted} rows."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.post("/calculate")
async def calculate_score(period: str = "30m", ticker: str = "SOXL", offset: int = 0, limit: int = 1000000, only_missing: bool = False, ids: str = None):
    """
    Calculate scores with Batching & Partial Update support.
    offset/limit: applied to the list of rows to be calculated.
    only_missing: if True, only process rows where total_score=0.
    ids: comma separated list of IDs to calculate specific rows (overrides offset/limit)
    """
    from db_lab import bulk_update_scores
    from db import get_connection
    from analysis import calculate_tech_indicators, calculate_holding_score, check_triple_filter, calculate_bbi, calculate_market_intelligence
    import json
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Select Target Rows (Limit/Offset/Condition)
            table = "lab_data_30m" if period == "30m" else "lab_data_5m"
            
            params = []
            where_clauses = ["ticker=%s"]
            params.append(ticker)
            
            # [IDs override]
            if ids:
                id_list = [int(x) for x in ids.split(',') if x.strip()]
                if id_list:
                    format_strings = ','.join(['%s'] * len(id_list))
                    where_clauses.append(f"id IN ({format_strings})")
                    params.extend(id_list)
                    # When IDs provided, ignore limit/offset/only_missing
                    sql = f"SELECT id, candle_time FROM {table} WHERE {' AND '.join(where_clauses)} ORDER BY candle_time ASC"
                    cursor.execute(sql, tuple(params))
                    target_rows = cursor.fetchall()
            else:
                if only_missing:
                    where_clauses.append("total_score = 0")
                
                # Fetch IDs and Times
                # Use params properly
                sql = f"SELECT id, candle_time FROM {table} WHERE {' AND '.join(where_clauses)} ORDER BY candle_time ASC LIMIT %s OFFSET %s"
                cursor.execute(sql, tuple(params + [limit, offset]))
                target_rows = cursor.fetchall()
            
            # Also load ALL data for History Context
            # Optimization: Load ALL data once for context?
            # If batch is small (200), loading 5000 rows context is fine.
            # If database grows to 1M, we need smarter context loading.
            # For now, load ALL for the ticker to ensure robust history lookups (simple & correct).
            # If memory issue, we can optimize later to load only needed range.
            
            cursor.execute("SELECT * FROM lab_data_30m WHERE ticker=%s ORDER BY candle_time ASC", (ticker,))
            all_30 = pd.DataFrame(cursor.fetchall())
            
            cursor.execute("SELECT * FROM lab_data_5m WHERE ticker=%s ORDER BY candle_time ASC", (ticker,))
            all_5m = pd.DataFrame(cursor.fetchall())
            
            # [Energy] Fetch UPRO data for context
            # [Energy] Fetch UPRO data for context (Use Main Table for matching period)
            cursor.execute(f"SELECT candle_time, open, close FROM {table} WHERE ticker='UPRO' ORDER BY candle_time ASC")
            all_upro = pd.DataFrame(cursor.fetchall())
            
    finally:
        conn.close()
        
    if not target_rows:
        return {"status": "success", "message": "No rows to process.", "updated_count": 0, "total_processed": 0}

    # Pre-process DataFrames
    # DB columns are usually lowercase. Analysis expects Capitalized or is mixed.
    # We standardize to Capitalized for compatibility with pandas_ta default.
    column_map = {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume', 'ma10': 'MA10', 'ma30': 'MA30'}
    
    if not all_30.empty: 
        all_30['candle_time'] = pd.to_datetime(all_30['candle_time'])
        all_30.rename(columns=column_map, inplace=True)
        # Type Cast to Float
        cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'MA10', 'MA30']
        for c in cols:
            if c in all_30.columns:
                all_30[c] = all_30[c].astype(float)
        
        all_30.set_index('candle_time', drop=False, inplace=True)
        all_30.sort_index(inplace=True)

    if not all_5m.empty: 
        all_5m['candle_time'] = pd.to_datetime(all_5m['candle_time'])
        all_5m.rename(columns=column_map, inplace=True)
        # Type Cast to Float
        cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'MA10', 'MA30']
        for c in cols:
            if c in all_5m.columns:
                all_5m[c] = all_5m[c].astype(float)
                
        all_5m.set_index('candle_time', drop=False, inplace=True)
        all_5m.sort_index(inplace=True)
        
    # Process UPRO Map
    upro_map = {}
    if not all_upro.empty:
        all_upro['candle_time'] = pd.to_datetime(all_upro['candle_time'])
        all_upro.rename(columns=column_map, inplace=True)
        # Type Cast
        cols = ['Open', 'Close']
        for c in cols:
            if c in all_upro.columns: 
                all_upro[c] = all_upro[c].astype(float)
                
        all_upro.set_index('candle_time', inplace=True)
        upro_map = all_upro[['Open', 'Close']].to_dict(orient='index') # {Timestamp: {'Open':..., 'Close':...}}
    
    # Algo Version
    ALGO_VER = "Jian Ver 1.0"
    updates = []
    
    print(f"[LAB] Batch Calc: {len(target_rows)} rows. (Offset {offset}, Limit {limit}, MissingOnly {only_missing})")

    # [Ver 8.0] Single-Source Simulation: 30m Data is Dynamically Generated from 5m.
    # PrevClose for Daily Change is fetched via YFinance if not local.
    
    import yfinance as yf
    # import pandas as pd # Removed to avoid UnboundLocalError
    import logging
    logger = logging.getLogger("uvicorn")

    # 1. Build PrevClose Map (Robust External Source)
    prev_close_map = {} 
    
    try:
        # Fetch 1mo history for ticker to get reliable daily closes
        # This solves "First candle of uploaded file doesn't know prev close"
        # Only fetch if we have a valid ticker
        if ticker in ['SOXL', 'SOXS', 'UPRO', 'TQQQ', 'SQQQ']:
            # Fetch 3mo to be safe
            logger.info(f"Fetching YFinance history for {ticker} (PrevClose)...")
            yf_ticker = yf.Ticker(ticker)
            # Standard Session Close
            hist = yf_ticker.history(period="3mo")
            # Convert to dict {date: close}
            # History index is (Date, or Datetime). normalize().
            for dt, row in hist.iterrows():
                prev_close_map[dt.date()] = row['Close']
            logger.info(f"YFinance Map Built: {len(prev_close_map)} days.")
    except Exception as e:
        logger.warning(f"YFinance Fetch Error: {e}")
        # Fallback to local data (last close of prev regular session)
        if not all_5m.empty:
            try:
                reg_session_df = all_5m.between_time('09:30', '16:00')
                daily_closes = reg_session_df.groupby(reg_session_df.index.date)['Close'].last()
                prev_close_map.update(daily_closes.to_dict())  # Merge local as fallback
            except: pass

    import math
    def clean_score(val):
        """Ensure score is valid int"""
        if val is None: return 0
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f): return 0
            return int(f)
        except: return 0

    for index, target in enumerate(target_rows):
        curr_time = pd.to_datetime(target['candle_time'])
        row_id = target['id']
        
        # 2. Get 5m Subset (The only truth)
        if not all_5m.empty:
            subset_5m = all_5m.loc[all_5m.index <= curr_time].tail(400) # Need enough for 30m resample
        else:
            subset_5m = pd.DataFrame()
            
        if len(subset_5m) < 1: continue

        # 3. Dynamic 30m Generation (The 'C3' Source)
        # Resample 5m -> 30m
        # Rule: closed='right', label='right' for standard candles?
        # 30m candle at 10:00 includes 09:35, 40, 45, 50, 55, 10:00.
        # We need to simulate "What did the 30m chart look like at 'curr_time'?"
        # If curr_time is 09:35, the 09:30-10:00 candle is INCOMPLETE. 
        # But signals are usually checked on completed candles or live?
        # Dashboard checks latest available 30m candle. 
        # If 09:35, the latest CLOSED 30m candle is 09:30. The CURRENT forming is 10:00.
        # That matches 'Live' behavior.
        
        try:
            # Resample logic
            sim_30m = subset_5m.resample('30min').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            # Calculate MA10, MA30 for this synthetic 30m
            # Using simple moving average
            sim_30m['MA10'] = sim_30m['Close'].rolling(window=10).mean()
            sim_30m['MA30'] = sim_30m['Close'].rolling(window=30).mean()
            
            # Calculate Tech? (MACD, RSI needed for full score?)
            # Actually, calculate_tech_indicators is called on 'main_subset'.
            # If period='5m', main is 5m.
            # But 'check_triple_filter' needs 30m context for Step 3.
            # So we pass sim_30m as 'data_30m'.
        except Exception as e:
            logger.warning(f"Resample Error {row_id}: {e}")
            sim_30m = pd.DataFrame()
            
        main_subset = subset_5m

        t5 = calculate_tech_indicators(main_subset) if not main_subset.empty else {}
        t30 = calculate_tech_indicators(sim_30m) if not sim_30m.empty else {}
        
        current_close = main_subset['Close'].iloc[-1]
        current_open = main_subset['Open'].iloc[-1]
        
        # [Fix] Determine Prev Close for this candle's date
        curr_date = curr_time.date()
        date_keys = sorted(list(prev_close_map.keys()))
        target_prev_close = 0.0

        # Load UPRO Context (Optional, for Energy)
        try:
             # Find Close of Previous Date
             past_dates = [d for d in date_keys if d < curr_date]
             if past_dates:
                 prev_date = past_dates[-1]
                 target_prev_close = float(prev_close_map[prev_date])
             else:
                 target_prev_close = current_open
        except:
             target_prev_close = current_open
             
        target_change = 0
        if target_prev_close > 0:
            target_change = ((current_close - target_prev_close) / target_prev_close) * 100
            
        upro_change = 0

        # [Fix] Explicitly Calculate 5m Moving Averages (MA10, MA30, MA12)
        # Reverted to MA30 per user request ("10/30 Matches Guideline")
        # Added MA12 for C2 Signal
        if not main_subset.empty and len(main_subset) >= 30:
            closes = main_subset['Close']
            ma10_5_val = closes.rolling(window=10).mean().iloc[-1]
            ma30_5_val = closes.rolling(window=30).mean().iloc[-1]
            ma12_5_val = closes.rolling(window=12).mean().iloc[-1]
        elif not main_subset.empty and len(main_subset) >= 12:
             # Fallback if length < 30 but >= 12
            closes = main_subset['Close']
            ma10_5_val = closes.rolling(window=10).mean().iloc[-1] if len(closes) >= 10 else 0
            ma30_5_val = 0
            ma12_5_val = closes.rolling(window=12).mean().iloc[-1]
        else:
            ma10_5_val = 0
            ma30_5_val = 0
            ma12_5_val = 0

        # [Ver 8.1] Signal Simulation (Trend Maintenance)
        # 1. Sig 1 (5m Trend) -> 10/30 Golden Cross or Alignment
        sig1 = (ma10_5_val > 0) and (ma30_5_val > 0) and (ma10_5_val >= ma30_5_val)
        
        # 3. Sig 3 (30m Trend - from Simulated 30m)
        ma10_30 = t30.get('ma10', 0)
        ma30_30 = t30.get('ma30', 0)
        if not sim_30m.empty:
             r = sim_30m.iloc[-1]
             m10 = r.get('MA10', 0)
             m30 = r.get('MA30', 0)
             if m10 > 0: ma10_30 = m10
             if m30 > 0: ma30_30 = m30
        sig3 = (ma10_30 > 0) and (ma30_30 > 0) and (ma10_30 >= ma30_30)
        
        # 2. Sig 2 (Breakout / Maintenance) -> Award if Price > 5m MA12
        sig2 = (ma12_5_val > 0) and (current_close > ma12_5_val)
        
        mock_v2_buy = {
            'buy_sig1_yn': 'Y' if sig1 else 'N',
            'buy_sig2_yn': 'Y' if sig2 else 'N',
            'buy_sig3_yn': 'Y' if sig3 else 'N',
        }
        
        # [Fix] Change Pct Calculation
        change_pct = 0.0
        oc = 0
        cc = 0
        if not main_subset.empty:
             oc = main_subset['Open'].iloc[-1]
             cc = main_subset['Close'].iloc[-1]
             if oc > 0:
                 change_pct = round(((cc - oc) / oc) * 100, 2)

        # [Fix] Calculate Market Intelligence (Vol, ATR, RSI, Pivot)
        # Use the same timeframe as tech indicators (30m simulated or 5m raw)
        target_df = sim_30m if period == '30m' else main_subset
        metrics = calculate_market_intelligence(target_df) if not target_df.empty else {}
        
        # Mock v2_res with metrics for scoring function
        v2_res = {
            'new_metrics': metrics,
            'current_price': current_close,
            'daily_change': change_pct # Use computed change_pct
        } 
        
        mock_v2_sell = {
            'sell_sig1_yn': 'N',
            'sell_sig2_yn': 'N',
            'sell_sig3_yn': 'N',
        }
        
        # BBI (Currently 0 as per previous request, but structure is here)
        # bbi_res = calculate_bbi(main_subset)
        # bbi_score = 10 if bbi_res.get('status') == 'BREAKOUT' else 0
        
        # Energy
        energy_target_change = target_change
        is_bull_ticker = (ticker in ['SOXL', 'TQQQ', 'UPRO', 'BULZ'])
        if not is_bull_ticker and target_change != 0:
             energy_target_change = -target_change
             
        energy_score = calculate_market_energy(energy_target_change, upro_change, is_bull=is_bull_ticker)

        score_data = calculate_holding_score(
            v2_res, t30 if period == '30m' else t5, mock_v2_buy, mock_v2_sell, bbi_score=0, energy_score=energy_score,
            strict_sum=False 
        )
        
        bd = score_data.get('breakdown', {})
        if offset == 0 and index < 3:
             logger.info(f"DEBUG SCORE {ticker} {curr_time}: {score_data}")
        
        s_c1 = 20 if mock_v2_buy['buy_sig1_yn'] == 'Y' else 0
        s_c2 = 20 if mock_v2_buy['buy_sig2_yn'] == 'Y' else 0 
        s_c3 = 20 if mock_v2_buy['buy_sig3_yn'] == 'Y' else 0
        
        s_en = clean_score(bd.get('energy', 0)) 
        s_atr = clean_score(bd.get('atr', 0))
        s_bbi = clean_score(bd.get('bbi', 0)) 
        
        s_rsi = clean_score(bd.get('rsi', 0))
        s_macd = clean_score(bd.get('macd', 0))
        s_vol = clean_score(bd.get('vol', 0))
        
        # Recalculate Total manually if needed, or trust score_data
        # If strict_sum=False, total might include what is available.
        total = s_c1 + s_c2 + s_c3 + s_en + s_atr + s_rsi + s_macd + s_vol + s_bbi # Added s_bbi
        
        calc_at = datetime.datetime.now()
        
        updates.append((
            total, s_c1, s_c2, s_c3, s_en, s_atr, s_bbi, s_rsi, s_macd, s_vol, ALGO_VER, calc_at, 
            change_pct, # Added Change Pct
            row_id
        ))

    # Bulk Update
    table_name = "lab_data_30m" if period == "30m" else "lab_data_5m"
    try:
        updated = bulk_update_scores(table_name, updates)
    except Exception as e:
        print(f"Bulk Update Error: {e}")
        # fallback
        updated = 0
    
    return {
        "status": "success", 
        "message": f"Processed {len(updates)} rows.",
        "updated_count": updated
    }

def calculate_trades_internal(data, buy_score, sell_score):
    """
    Internal logic to calculate trades based on score thresholds.
    Matches the logic in frontend LabPage.jsx
    """
    if not data: return []

    trades = []
    position = None # {'price', 'time', 'score'}

    # Expects data sorted by time ASC
    for d in data:
        p = float(d['close'])
        s = int(d['total_score'])
        t = d['candle_time']

        # [Ver 9.5.4] Skip invalid/uncalculated scores for signals
        # But we still iterate so 'data[-1]' at the end will be correct for Open Position
        if s == 0: continue

        if position is None:
            # Buy Condition
            if s >= buy_score:
                position = {'price': p, 'time': t, 'score': s}
        else:
            # Sell Condition
            if s <= sell_score:
                yield_pct = round(((p - position['price']) / position['price'] * 100), 2)
                trades.append({
                    'entryTime': position['time'],
                    'entryPrice': position['price'],
                    'entryScore': position['score'],
                    'exitTime': t,
                    'exitPrice': p,
                    'exitScore': s,
                    'yield': yield_pct
                })
                position = None

    # [Ver 9.5.3] Check for Open Position (Holding)
    if position is not None and len(data) > 0:
        # Calculate floating yield based on the LATEST available data point
        last_d = data[-1]
        last_p = float(last_d['close'])
        last_s = int(last_d['total_score'])
        # last_t = last_d['candle_time'] # Not strictly exit time, but current time
        
        yield_pct = round(((last_p - position['price']) / position['price'] * 100), 2)
        trades.append({
            'entryTime': position['time'],
            'entryPrice': position['price'],
            'entryScore': position['score'],
            'exitTime': None, # Indicates OPEN
            'exitPrice': last_p, # Current Price
            'exitScore': last_s, # Current Score
            'yield': yield_pct,
            'isOpen': True
        })
    
    # Return newest first
    return trades[::-1]

@router.get("/backtest/{ticker}")
def get_lab_backtest(ticker: str, period: str = "5m", limit: int = 2000, buy_score: int = None, sell_score: int = None):
    """
    Get Signal Returns (historical trades) based on Lab settings.
    If buy_score/sell_score provided, use them for simulation. 
    Otherwise use global config.
    """
    from db import get_global_config, get_connection
    
    if buy_score is None:
        buy_score = int(get_global_config("lab_buy_score", 70))
    if sell_score is None:
        sell_score = int(get_global_config("lab_sell_score", 50))

    table = "lab_data_30m" if period == "30m" else "lab_data_5m"
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # [Ver 9.5.4] Fetch recent history with Limit & Latest Data (Allow 0 score)
            # Use DESC LIMIT to get latest, then reverse.
            sql = f"SELECT candle_time, close, total_score FROM {table} WHERE ticker=%s ORDER BY candle_time DESC LIMIT %s"
            cursor.execute(sql, (ticker, limit))
            rows = cursor.fetchall()
            
            # Sort ASC for calculation
            rows = rows[::-1]
            
            # Serialize for internal calculation
            data = []
            for r in rows:
                data.append({
                    'candle_time': r['candle_time'].isoformat() if isinstance(r['candle_time'], datetime.datetime) else r['candle_time'],
                    'close': float(r['close']),
                    'total_score': int(r['total_score'])
                })
                
            trades = calculate_trades_internal(data, buy_score, sell_score)
            
            return {
                "status": "success",
                "ticker": ticker,
                "buy_score": buy_score,
                "sell_score": sell_score,
                "trades": trades
            }
    finally:
        conn.close()
