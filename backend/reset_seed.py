
import logging
from datetime import datetime, timedelta
import pytz
import pandas as pd
import yfinance as yf
from db import get_connection, save_market_candles

# Config
TARGET_TICKERS = ["SOXL", "SOXS", "UPRO"]
DAYS_HISTORY = 30
TZ_NY = pytz.timezone('America/New_York')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ResetSeed")

def reset_and_seed():
    conn = get_connection()
    try:
        # 1. Truncate Tables
        logger.info("🗑️  Truncating market_candles & signal_history...")
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE market_candles")
            cursor.execute("TRUNCATE TABLE signal_history")
            # Also clear cache in analysis.py? No, process restart will handle it.
        conn.commit()
        
        # 2. Fetch and Seed Data
        logger.info(f"🌱 Seeding {DAYS_HISTORY} days of data for {TARGET_TICKERS}...")
        
        for ticker in TARGET_TICKERS:
            # 30m Data
            logger.info(f"  > Fetching {ticker} 30m...")
            df_30 = yf.download(ticker, period="1mo", interval="30m", progress=False)
            if not df_30.empty:
                # Fix columns if MultiIndex
                if isinstance(df_30.columns, pd.MultiIndex):
                    df_30.columns = df_30.columns.get_level_values(0)
                
                # Convert Timezone to NY
                if df_30.index.tz is None:
                    # YFinance 1mo/30m is usually locally aware or UTC? 
                    # Actually yfinance returns local exchange time usually but localized.
                    # Let's assume it might be naive NY or UTC. 
                    # Safer: Localize as NY if naive? No, yf usually returns tz-aware now.
                     df_30.index = df_30.index.tz_localize('America/New_York')
                else:
                    df_30.index = df_30.index.tz_convert(TZ_NY)
                
                logging.info(f"    - First: {df_30.index[0]}")
                logging.info(f"    - Last:  {df_30.index[-1]}")
                
                save_market_candles(ticker, "30m", df_30, "yfinance_seed")
            
            # 5m Data
            logger.info(f"  > Fetching {ticker} 5m...")
            df_5 = yf.download(ticker, period="1mo", interval="5m", progress=False)
            if not df_5.empty:
                if isinstance(df_5.columns, pd.MultiIndex):
                    df_5.columns = df_5.columns.get_level_values(0)
                    
                if df_5.index.tz is None:
                     df_5.index = df_5.index.tz_localize('America/New_York')
                else:
                    df_5.index = df_5.index.tz_convert(TZ_NY)
                    
                save_market_candles(ticker, "5m", df_5, "yfinance_seed")
        
        logger.info("✅ Database Reset & Seed Completed!")
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    reset_and_seed()
