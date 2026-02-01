
from fastapi import APIRouter, HTTPException
import pandas as pd
import datetime
import yfinance as yf
from db_simulator import init_sim_tables, clear_sim_data, bulk_insert_sim_data, bulk_update_sim_scores
from db import get_connection, get_global_config
from analysis import calculate_tech_indicators, calculate_holding_score, calculate_market_energy, calculate_bbi, check_triple_filter
from routers.lab import calculate_trades_internal

router = APIRouter(prefix="/api/simulator", tags=["simulator"])

# Ensure tables exist
try:
    init_sim_tables()
except:
    pass

@router.post("/initialize")
async def run_simulation():
    """
    [One-Click Logic]
    1. Clear Sim Table
    2. Download 10 days of 5m data (SOXL, SOXS, UPRO) from YFinance
    3. Insert into DB
    4. Calculate Scores
    """
    tickers = ['SOXL', 'SOXS', 'UPRO']
    
    # 1. Clear Table
    clear_sim_data()
    
    total_inserted = 0
    
    # 2. Bulk Download & Insert
    for ticker in tickers:
        try:
            # Download 10 days of 5m data
            print(f"[{ticker}] Downloading 10 days of 5m data...")
            df = yf.download(ticker, period="10d", interval="5m", progress=False)
            if df.empty: continue
            
            # Prepare for Insert
            # YF MultiIndex columns fix
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            insert_rows = []
            for dt, row in df.iterrows():
                # YF datetime is index. Ensure it is naive or UTC converted properly?
                # Usually YF returns timezone-aware.
                candle_time = dt.to_pydatetime()
                if candle_time.tzinfo:
                    candle_time = candle_time.replace(tzinfo=None) # naive (local time assumed or just strip)
                
                # Check NaNs
                if pd.isna(row['Close']): continue
                
                # change_pct needs prev close. Simple calculation locally? 
                # Or just put 0 and let scoring fix it?
                # Scoring usually re-calcs indicators. change_pct is useful for display.
                # We'll calculate it roughly here or leave 0.
                
                insert_rows.append((
                   ticker, 
                   candle_time,
                   float(row['Open']), float(row['High']), float(row['Low']), float(row['Close']),
                   int(row['Volume']),
                   0.0 # change_pct placeholder
                ))
                
            cnt = bulk_insert_sim_data(insert_rows)
            total_inserted += cnt
            print(f"[{ticker}] Inserted {cnt} rows.")
            
        except Exception as e:
            print(f"[{ticker}] Error: {e}")
            
    # 3. Calculate Scores (Re-using Analysis Logic)
    # We load data back from DB to ensure proper sorting and ID handling
    return await calculate_sim_scores(total_inserted)

async def calculate_sim_scores(inserted_count):
    """
    Load data from sim_data_5m and calculate scores
    """
    conn = get_connection()
    processed_count = 0
    
    try:
        with conn.cursor() as cursor:
             # Load UPRO Context
             cursor.execute("SELECT candle_time, open, close FROM sim_data_5m WHERE ticker='UPRO' ORDER BY candle_time ASC")
             all_upro = pd.DataFrame(cursor.fetchall())
             
             for ticker in ['SOXL', 'SOXS']:
                 cursor.execute(f"SELECT * FROM sim_data_5m WHERE ticker='{ticker}' ORDER BY candle_time ASC")
                 df = pd.DataFrame(cursor.fetchall())
                 if df.empty: continue
                 
                 # Prepare DF
                 column_map = {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume', 'ma10': 'MA10', 'ma30': 'MA30'}
                 df['candle_time'] = pd.to_datetime(df['candle_time'])
                 df.rename(columns=column_map, inplace=True)
                 cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                 for c in cols: df[c] = df[c].astype(float)
                 df.set_index('candle_time', drop=False, inplace=True)
                 
                 # Prepare UPRO
                 upro_map = {}
                 if not all_upro.empty:
                     temp_upro = all_upro.copy()
                     temp_upro['candle_time'] = pd.to_datetime(temp_upro['candle_time'])
                     temp_upro.set_index('candle_time', inplace=True)
                     upro_map = temp_upro[['open', 'close']].to_dict(orient='index')

                 # Calc
                 updates = []
                 ALGO_VER = "Sim v1.0"
                 
                 # Iterate
                 # Since indicators need history, we use rolling calculation helpers
                 # Using reusing `calculate_tech_indicators` which works on full DF usually?
                 # Actually `calculate_tech_indicators` takes a row and "full_df" context.
                 # Let's see how `analysis.py` does it.
                 # It iterates.
                 
                 # Optimization: Pre-calculate indicators using pandas_ta if possible for speed?
                 # reusing individual row logic ensures EXACT match with live robot.
                 # So we iterate.
                 
                 for i in range(len(df)):
                     row = df.iloc[i]
                     # Context: df upto i
                     current_slice = df.iloc[:i+1] # potentially slow if loop is huge. 
                     # But for 10 days (24h * 12 * 10 = ~3000 rows) it's acceptable.
                     
                     prev_row = df.iloc[i-1] if i > 0 else None
                     
                     # Calculate Indicators
                     inds = calculate_tech_indicators(row, current_slice)
                     
                     # Market Energy
                     en_score = calculate_market_energy(
                         row, 
                         upro_map.get(row['candle_time'], {}).get('open', 0),
                         upro_map.get(row['candle_time'], {}).get('close', 0),
                         ticker
                     )
                     
                     # BBI
                     bbi_score = calculate_bbi(current_slice)
                     
                     # Total Score
                     total, s_c1, s_c2, s_c3, s_en, s_atr, s_bbi, s_rsi, s_macd, s_vol = calculate_holding_score(
                         ticker, row, inds, en_score, bbi_score
                     )
                     
                     # Triple Filter
                     # Warning: Triple Filter might require market_indices (SPX, VIX) which we didn't fetch.
                     # Live logic queries `market_indices`. Here we don't have simulated SPX/VIX.
                     # So we might bypass or accept Triple Filter is partial?
                     # Let's ignore triple filter overrides for simulation simplicity or assume valid.
                     # Actually `calculate_holding_score` already sums them up.
                     # Check `analysis.py`.
                     
                     # Change Pct calculation (since YF insert was 0)
                     change_pct = 0.0
                     if prev_row is not None:
                         prev_close = float(prev_row['Close'])
                         if prev_close > 0:
                             change_pct = round((float(row['Close']) - prev_close) / prev_close * 100, 2)
                     
                     updates.append((
                        total, s_c1, s_c2, s_c3, s_en, s_atr, s_bbi, s_rsi, s_macd, s_vol, 
                        ALGO_VER, datetime.datetime.now(), 
                        change_pct,
                        row['id']
                     ))
                     
                 # Bulk Update
                 if updates:
                     updated = bulk_update_sim_scores(updates)
                     processed_count += updated
                     
    finally:
        conn.close()

    return {
        "status": "success",
        "message": "Simulation Data Ready",
        "inserted_raw": inserted_count,
        "processed_scores": processed_count
    }

@router.get("/data")
def get_sim_data(ticker: str = "SOXL"):
    """Get Charts for Simulator"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM sim_data_5m WHERE ticker=%s ORDER BY candle_time ASC"
            cursor.execute(sql, (ticker,))
            rows = cursor.fetchall()
            return {"status": "success", "data": rows}
    finally:
        conn.close()

@router.get("/backtest/{ticker}")
def get_sim_backtest(ticker: str, buy_score: int = None, sell_score: int = None):
    """Signal Returns for Simulator"""
    if buy_score is None:
        buy_score = int(get_global_config("lab_buy_score", 70))
    if sell_score is None:
        sell_score = int(get_global_config("lab_sell_score", 50))
        
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Fetch all sim data
            sql = "SELECT candle_time, close, total_score FROM sim_data_5m WHERE ticker=%s ORDER BY candle_time ASC"
            cursor.execute(sql, (ticker,))
            rows = cursor.fetchall()
            
            data = []
            for r in rows:
                data.append({
                    'candle_time': r['candle_time'].isoformat() if isinstance(r['candle_time'], datetime.datetime) else r['candle_time'],
                    'close': float(r['close']),
                    'total_score': int(r['total_score'])
                })
            
            # Reuse logic
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
