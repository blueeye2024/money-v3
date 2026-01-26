
import sys
import os
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

import pandas as pd
from backend.db import get_connection
from backend.analysis import calculate_tech_indicators, calculate_holding_score, check_triple_filter, calculate_bbi, calculate_market_energy

def test_lab_logic():
    ticker = "SOXL"
    period = "30m"
    limit = 10
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Load Data (Mimic lab.py)
            cursor.execute("SELECT * FROM lab_data_30m WHERE ticker=%s ORDER BY candle_time ASC", (ticker,))
            all_30 = pd.DataFrame(cursor.fetchall())
            
            cursor.execute("SELECT * FROM lab_data_5m WHERE ticker=%s ORDER BY candle_time ASC", (ticker,))
            all_5m = pd.DataFrame(cursor.fetchall())
            
            # [Energy] Fetch UPRO data
            cursor.execute("SELECT candle_time, open, close FROM lab_data_30m WHERE ticker='UPRO' ORDER BY candle_time ASC")
            all_upro = pd.DataFrame(cursor.fetchall())
    finally:
        conn.close()

    column_map = {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume', 'ma10': 'MA10', 'ma30': 'MA30'}
    
    if not all_30.empty: 
        all_30['candle_time'] = pd.to_datetime(all_30['candle_time'])
        all_30.rename(columns=column_map, inplace=True)
        all_30.set_index('candle_time', drop=False, inplace=True)
        all_30.sort_index(inplace=True)

    if not all_5m.empty: 
        all_5m['candle_time'] = pd.to_datetime(all_5m['candle_time'])
        all_5m.rename(columns=column_map, inplace=True)
        all_5m.set_index('candle_time', drop=False, inplace=True)
        all_5m.sort_index(inplace=True)
        
    upro_map = {}
    if not all_upro.empty:
        all_upro['candle_time'] = pd.to_datetime(all_upro['candle_time'])
        all_upro.rename(columns=column_map, inplace=True)
        all_upro.set_index('candle_time', inplace=True)
        upro_map = all_upro[['Open', 'Close']].to_dict(orient='index')

    print(f"Data Loaded. 30m: {len(all_30)}, UPRO: {len(upro_map)}")
    
    # Process Loop
    target_rows = all_30.tail(limit).to_dict('records') # Mimic target list
    
    for row in target_rows:
        curr_time = row['candle_time'] # Already timestamp due to conversion
        # Wait, in lab.py target_rows comes from DB fetch (dict), NOT dataframe.
        # But here I converted all_30 to DF. 
        # In lab.py: target_rows = cursor.fetchall().
        # 'candle_time' in dict is datetime object or string? DB returns datetime usually.
        # But here 'curr_time' is Timestamp.
        
        # In lab.py:
        # curr_time = pd.to_datetime(target['candle_time'])
        
        # Let's mimic exact lab.py logic
        
        subset_30 = pd.DataFrame()
        if not all_30.empty:
            subset_30 = all_30.loc[all_30.index <= curr_time].tail(300)
            
        subset_5m = pd.DataFrame()
        if not all_5m.empty:
            subset_5m = all_5m.loc[all_5m.index <= curr_time].tail(300)
            
        # UPRO Logic
        upro_change = 0
        if upro_map:
            upro_row = upro_map.get(curr_time)
            if upro_row:
                uc = upro_row['Close']
                uo = upro_row['Open']
                if uo > 0:
                    upro_change = ((uc - uo) / uo) * 100
        
        if len(subset_30) < 1: continue

        # Analysis
        t30 = calculate_tech_indicators(subset_30) if not subset_30.empty else {}
        t5 = calculate_tech_indicators(subset_5m) if not subset_5m.empty else {}
        
        current_close = 0
        current_open = 0
        if not subset_30.empty:
             current_close = subset_30['Close'].iloc[-1]
             current_open = subset_30['Open'].iloc[-1]
        
        target_change = 0
        if current_open > 0:
            target_change = ((current_close - current_open) / current_open) * 100
            
        d30_map = {ticker: subset_30}
        d5_map = {ticker: subset_5m}
        v2_res = check_triple_filter(ticker, d30_map, d5_map, override_price=current_close)
        bbi_res = calculate_bbi(subset_30)
        bbi_val = bbi_res.get('bbi', 0)
        
        is_bull_ticker = (ticker == 'SOXL')
        
        energy_target_change = target_change
        if not is_bull_ticker and target_change != 0:
             energy_target_change = -target_change
             
        energy_score = calculate_market_energy(energy_target_change, upro_change, is_bull=is_bull_ticker)
        
        print(f"Calc Row {curr_time}: En={energy_score}")
        
        mock_v2_buy = { 'buy_sig1_yn': 'N', 'buy_sig2_yn': 'N', 'buy_sig3_yn': 'N' }
        mock_v2_sell = { 'sell_sig1_yn': 'N', 'sell_sig2_yn': 'N', 'sell_sig3_yn': 'N' }
        
        score_data = calculate_holding_score(
            v2_res, t30, mock_v2_buy, mock_v2_sell, bbi_score=bbi_val, energy_score=energy_score
        )
        print("Score Data:", score_data.get('score'))

if __name__ == "__main__":
    test_lab_logic()
