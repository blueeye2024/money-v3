
import sys
import os
from datetime import datetime
import pytz

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_lab import save_realtime_lab_data

def test_lab_save():
    print("Testing save_realtime_lab_data manually...")
    
    # Create US Timestamp
    utc = pytz.utc
    eastern = pytz.timezone('US/Eastern')
    now_utc = datetime.now(utc)
    now_est = now_utc.astimezone(eastern)
    candle_time_us = now_est.replace(second=0, microsecond=0)
    
    print(f"Using Candle Time (US): {candle_time_us}")
    
    # Dummy Data
    dummy_data = [{
        'ticker': 'TEST_LB',
        'candle_time': candle_time_us,
        'open': 100.0,
        'high': 105.0,
        'low': 99.0,
        'close': 102.5,
        'volume': 12345,
        'ma10': 101.0,
        'ma30': 98.0,
        'change_pct': 2.5,
        'scores': {
            'total': 85,
            'sig1': 1, 'sig2': 1, 'sig3': 0,
            'energy': 80,
            'atr': 20,
            'bbi': 5.5,
            'rsi': 60,
            'macd': 10,
            'vol': 5
        }
    }]
    
    try:
        count = save_realtime_lab_data(dummy_data)
        if count == 1:
            print("✅ Successfully inserted 1 row.")
        else:
            print(f"❌ Insertion count mismatch: {count}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_lab_save()
