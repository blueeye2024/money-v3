"""
Data Validation and Auto-Fill Module
Ensures sufficient candle data for accurate SMA calculations
"""

from db import load_market_candles, save_market_candles, get_connection
import yfinance as yf
import pandas as pd
from datetime import datetime

# Minimum required candles for accurate analysis
MIN_CANDLES_30M = 50  # For SMA30 calculation with buffer
MIN_CANDLES_5M = 100   # For SMA30 calculation with buffer
MIN_CANDLES_1D = 180   # 6 months of daily data

def validate_and_fill_data(ticker, timeframe, min_required):
    """
    Validate candle data and auto-fill if insufficient
    
    Args:
        ticker: Stock ticker (e.g., 'SOXL')
        timeframe: '5m', '30m', or '1d'
        min_required: Minimum number of candles required
    
    Returns:
        DataFrame with validated data, or None if failed
    """
    print(f"🔍 Validating {ticker} {timeframe} data...")
    
    # Load from DB
    df = load_market_candles(ticker, timeframe, limit=min_required)
    
    # Check if data exists and is sufficient
    if df is None or df.empty:
        print(f"  ❌ No data found. Fetching from yfinance...")
        return fetch_and_save(ticker, timeframe, min_required)
    
    # Check data quality
    valid_count = df['Close'].notna().sum()
    
    if len(df) < min_required or valid_count < min_required:
        print(f"  ⚠️  Insufficient data: {len(df)}/{min_required} candles, {valid_count} valid")
        print(f"  📥 Fetching additional data...")
        return fetch_and_save(ticker, timeframe, min_required)
    
    print(f"  ✅ Data OK: {len(df)} candles, {valid_count} valid")
    return df

def fetch_and_save(ticker, timeframe, min_required):
    """
    Fetch data from yfinance and save to DB
    
    Args:
        ticker: Stock ticker
        timeframe: '5m', '30m', or '1d'
        min_required: Minimum number of candles required
    
    Returns:
        DataFrame with fetched data
    """
    try:
        # Map timeframe to yfinance parameters
        period_map = {
            '5m': ('5d', '5m'),    # 5 days of 5-minute data
            '30m': ('1mo', '30m'),  # 1 month of 30-minute data
            '1d': ('6mo', '1d')     # 6 months of daily data
        }
        
        if timeframe not in period_map:
            print(f"  ❌ Invalid timeframe: {timeframe}")
            return None
        
        period, interval = period_map[timeframe]
        
        print(f"  📡 Fetching {ticker} {interval} data (period={period})...")
        df = yf.download(ticker, period=period, interval=interval, 
                        prepost=True, progress=False, timeout=20)
        
        if df is None or df.empty:
            print(f"  ❌ yfinance returned empty data")
            return None
        
        # Clean data
        df = df.dropna(subset=['Close'])  # Remove None values
        
        # Normalize timestamps for 1d
        if timeframe == '1d':
            df.index = df.index.normalize()  # Set to 00:00:00
        
        # Normalize timestamps for 30m (keep only :00 or :30)
        if timeframe == '30m':
            df = df[df.index.minute.isin([0, 30])]
        
        print(f"  💾 Saving {len(df)} candles to DB...")
        save_market_candles(ticker, timeframe, df, source='yfinance')
        
        # Reload from DB to ensure consistency
        df_reloaded = load_market_candles(ticker, timeframe, limit=min_required)
        
        if df_reloaded is not None and len(df_reloaded) >= min_required:
            print(f"  ✅ Successfully saved and reloaded {len(df_reloaded)} candles")
            return df_reloaded
        else:
            print(f"  ⚠️  Reloaded data insufficient: {len(df_reloaded) if df_reloaded is not None else 0}")
            return df_reloaded
            
    except Exception as e:
        print(f"  ❌ Error fetching data: {e}")
        return None

def validate_all_tickers(tickers=['SOXL', 'SOXS', 'UPRO']):
    """
    Validate data for all core tickers
    
    Args:
        tickers: List of tickers to validate
    
    Returns:
        Dict of {ticker: {timeframe: DataFrame}}
    """
    print("=" * 60)
    print("🔍 DATA VALIDATION & AUTO-FILL")
    print("=" * 60)
    
    results = {}
    
    for ticker in tickers:
        print(f"\n📊 Validating {ticker}...")
        results[ticker] = {}
        
        # Validate 30m data
        df_30m = validate_and_fill_data(ticker, '30m', MIN_CANDLES_30M)
        results[ticker]['30m'] = df_30m
        
        # Validate 5m data
        df_5m = validate_and_fill_data(ticker, '5m', MIN_CANDLES_5M)
        results[ticker]['5m'] = df_5m
        
        # Validate 1d data
        df_1d = validate_and_fill_data(ticker, '1d', MIN_CANDLES_1D)
        results[ticker]['1d'] = df_1d
    
    print("\n" + "=" * 60)
    print("✅ VALIDATION COMPLETE")
    print("=" * 60)
    
    return results

if __name__ == '__main__':
    validate_all_tickers()
