import sys
import os
sys.path.append(os.getcwd())
import pandas as pd
from db import get_connection
from analysis import calculate_tech_indicators, calculate_holding_score, check_triple_filter, calculate_bbi

ticker = "SOXL"
conn = get_connection()
try:
    with conn.cursor() as cursor:
        # 30m
        cursor.execute(f"SELECT * FROM lab_data_30m WHERE ticker='{ticker}' ORDER BY candle_time ASC")
        rows_30 = cursor.fetchall()
        df_30 = pd.DataFrame(rows_30)
        
        # 5m
        cursor.execute(f"SELECT * FROM lab_data_5m WHERE ticker='{ticker}' ORDER BY candle_time ASC")
        rows_5m = cursor.fetchall()
        df_5m = pd.DataFrame(rows_5m)
finally:
    conn.close()

if not df_30.empty: df_30['candle_time'] = pd.to_datetime(df_30['candle_time'])
if not df_5m.empty: df_5m['candle_time'] = pd.to_datetime(df_5m['candle_time'])

print(f"Loaded 30m: {len(df_30)}, 5m: {len(df_5m)}")
if not df_30.empty:
    print("First Row 30m:", df_30.iloc[0]['candle_time'])

# Run logic check
target_df = df_30
for i in range(len(target_df)):
    row = target_df.iloc[i]
    curr_time = row['candle_time']
    # Just checking one
    if i > 0: break
    
    subset = df_30[df_30['candle_time'] <= curr_time].tail(50)
    print(f"Subset Len: {len(subset)}")
    print("Test OK")

