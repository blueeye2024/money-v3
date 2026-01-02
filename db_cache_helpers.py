# Add to db.py at the end (after get_user_requests)

def save_price_cache(ticker, price_data):
    """Save KIS API price to cache"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO price_cache (ticker, price, diff, rate, exchange)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    price = VALUES(price),
                    diff = VALUES(diff),
                    rate = VALUES(rate),
                    exchange = VALUES(exchange),
                    updated_at = CURRENT_TIMESTAMP
                """
                cursor.execute(sql, (
                    ticker,
                    price_data.get('price', 0),
                    price_data.get('diff', 0),
                    price_data.get('rate', 0),
                    price_data.get('exchange', 'UNKNOWN')
                ))
            conn.commit()
    except Exception as e:
        print(f"Save Price Cache Error: {e}")

def get_price_cache(ticker):
    """Retrieve latest cached price for ticker"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT price, diff, rate, exchange, updated_at FROM price_cache WHERE ticker=%s",
                    (ticker,)
                )
                result = cursor.fetchone()
                if result:
                    return {
                        'price': float(result['price']),
                        'diff': float(result['diff']),
                        'rate': float(result['rate']),
                        'exchange': result['exchange'],
                        'cached_at': result['updated_at']
                    }
    except Exception as e:
        print(f"Get Price Cache Error: {e}")
    return None

def save_candle_data(ticker, interval, candles_df):
    """
    Save candle dataframe to DB
    candles_df: pandas DataFrame with DatetimeIndex and columns [Open, High, Low, Close, Volume]
    interval: '5m' or '30m'
    """
    if candles_df is None or candles_df.empty:
        return
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # Take last 100 candles to limit DB size
                recent = candles_df.tail(100)
                
                for idx, row in recent.iterrows():
                    sql = """
                    INSERT INTO candle_data (ticker, interval, candle_time, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        open = VALUES(open),
                        high = VALUES(high),
                        low = VALUES(low),
                        close = VALUES(close),
                        volume = VALUES(volume),
                        updated_at = CURRENT_TIMESTAMP
                    """
                    cursor.execute(sql, (
                        ticker, interval,
                        idx.to_pydatetime().replace(microsecond=0),
                        float(row['Open']),
                        float(row['High']),
                        float(row['Low']),
                        float(row['Close']),
                        int(row['Volume']) if 'Volume' in row else 0
                    ))
            conn.commit()
    except Exception as e:
        print(f"Save Candle Data Error ({ticker}/{interval}): {e}")

def get_candle_data(ticker, interval, limit=100):
    """
    Retrieve cached candle data from DB
    Returns pandas DataFrame with DatetimeIndex
    """
    import pandas as pd
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                SELECT candle_time, open, high, low, close, volume
                FROM candle_data
                WHERE ticker=%s AND interval=%s
                ORDER BY candle_time DESC
                LIMIT %s
                """
                cursor.execute(sql, (ticker, interval, limit))
                rows = cursor.fetchall()
                
                if rows:
                    df = pd.DataFrame(rows)
                    df['candle_time'] = pd.to_datetime(df['candle_time'])
                    df = df.set_index('candle_time').sort_index()
                    df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                    return df
    except Exception as e:
        print(f"Get Candle Data Error ({ticker}/{interval}): {e}")
    return None
