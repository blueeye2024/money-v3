
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import get_connection
from analysis import check_triple_filter, calculate_holding_score, calculate_tech_indicators, calculate_bbi, fetch_data
import pandas as pd

def debug_soxs():
    ticker = "SOXS"
    
    # 1. Fetch Data
    print("Fetching Data...")
    start_ch = pd.Timestamp.now()
    data_30m, data_5m, data_1d, market, regime = fetch_data()
    print(f"Fetch Time: {pd.Timestamp.now() - start_ch}")
    
    if ticker not in data_30m:
        print("No Data for SOXS")
        return

    # 2. Run check_triple_filter (V2 Logic)
    print("Running V2 Logic...")
    v2_res = check_triple_filter(ticker, data_30m, data_5m)
    
    print("\n[V2 Result (Fresh Algo)]")
    print(f"Step 1 (30m Trend): {v2_res.get('step1')}")
    print(f"Step 2 (Pullback):  {v2_res.get('step2')}")
    print(f"Step 3 (Timing):    {v2_res.get('step3')}")
    
    fresh_v2_buy = {
        'buy_sig1_yn': 'Y' if v2_res.get('step1') else 'N',
        'buy_sig2_yn': 'Y' if v2_res.get('step2') else 'N',
        'buy_sig3_yn': 'Y' if v2_res.get('step3') else 'N'
    }
    print(f"Fresh V2 Buy Struct: {fresh_v2_buy}")
    
    # 3. Techs & BBI
    df_5m = data_5m[ticker]
    df_30 = data_30m[ticker]
    techs = calculate_tech_indicators(df_5m)
    
    bbi_score = 0
    if not df_30.empty:
        bbi_res = calculate_bbi(df_30)
        bbi_score = bbi_res.get('bbi', 0)
    
    print(f"\n[Indicators]")
    print(f"RSI: {techs.get('rsi')}")
    print(f"MACD: {techs.get('macd')}")
    print(f"BBI Score: {bbi_score}")

    # 4. Calculate Score
    print("\n[Score Calculation]")
    score_model = calculate_holding_score(
        v2_res, 
        techs, 
        v2_buy=fresh_v2_buy, 
        v2_sell=None, 
        bbi_score=bbi_score
    )
    
    print(f"Total Score: {score_model.get('score')}")
    print("Breakdown:")
    print(score_model.get('breakdown'))

if __name__ == "__main__":
    debug_soxs()
