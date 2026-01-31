
import pymysql
from db import get_connection

def init_lab_tables():
    """Create lab_data_30m and lab_data_5m tables if not exist."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 30m Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lab_data_30m (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ticker VARCHAR(10) NOT NULL,
                    candle_time DATETIME NOT NULL,
                    open DECIMAL(20, 4),
                    high DECIMAL(20, 4),
                    low DECIMAL(20, 4),
                    close DECIMAL(20, 4),
                    volume BIGINT,
                    ma10 DECIMAL(20, 4),
                    ma30 DECIMAL(20, 4),
                    change_pct DECIMAL(10, 4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    /* Phase 2: Score Columns */
                    total_score INT DEFAULT 0,
                    score_cheongan_1 INT DEFAULT 0,
                    score_cheongan_2 INT DEFAULT 0,
                    score_cheongan_3 INT DEFAULT 0,
                    score_energy INT DEFAULT 0,
                    score_atr INT DEFAULT 0,
                    score_bbi INT DEFAULT 0,
                    score_rsi INT DEFAULT 0,
                    score_macd INT DEFAULT 0,
                    score_vol INT DEFAULT 0,
                    score_slope DECIMAL(10, 1) DEFAULT 0,
                    algo_version VARCHAR(20),
                    calculated_at DATETIME,
                    
                    UNIQUE KEY unique_candle (ticker, candle_time)
                );
            """)
            
            # 5m Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lab_data_5m (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ticker VARCHAR(10) NOT NULL,
                    candle_time DATETIME NOT NULL,
                    open DECIMAL(20, 4),
                    high DECIMAL(20, 4),
                    low DECIMAL(20, 4),
                    close DECIMAL(20, 4),
                    volume BIGINT,
                    ma10 DECIMAL(20, 4),
                    ma30 DECIMAL(20, 4),
                    change_pct DECIMAL(10, 4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    /* Phase 2: Score Columns */
                    total_score INT DEFAULT 0,
                    score_cheongan_1 INT DEFAULT 0,
                    score_cheongan_2 INT DEFAULT 0,
                    score_cheongan_3 INT DEFAULT 0,
                    score_energy INT DEFAULT 0,
                    score_atr INT DEFAULT 0,
                    score_bbi INT DEFAULT 0,
                    score_rsi INT DEFAULT 0,
                    score_macd INT DEFAULT 0,
                    score_vol INT DEFAULT 0,
                    score_slope DECIMAL(10, 1) DEFAULT 0,
                    algo_version VARCHAR(20),
                    calculated_at DATETIME,
                    
                    UNIQUE KEY unique_candle (ticker, candle_time)
                );
            """)

            # Add columns if they missed (for existing tables)
            # Simple approach: Ignore error or check info schema. 
            # Quick check: Attempt ADD COLUMN and catch 'Duplicate column name'
            score_cols = [
                "total_score INT DEFAULT 0",
                "score_cheongan_1 INT DEFAULT 0",
                "score_cheongan_2 INT DEFAULT 0",
                "score_cheongan_3 INT DEFAULT 0",
                "score_energy INT DEFAULT 0",
                "score_atr INT DEFAULT 0",
                "score_bbi INT DEFAULT 0", # Fixed: was missing
                "score_rsi INT DEFAULT 0",
                "score_macd INT DEFAULT 0",
                "score_vol INT DEFAULT 0",
                "score_slope DECIMAL(10, 1) DEFAULT 0",
                "algo_version VARCHAR(20)",
                "calculated_at DATETIME"
            ]
            
            for table in ['lab_data_30m', 'lab_data_5m']:
                for col_def in score_cols:
                    col_name = col_def.split(' ')[0]
                    try:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
                    except Exception as e:
                        # 1060: Duplicate column name
                        pass

        conn.commit()
        conn.commit()
        print("✅ Lab Tables Initialized (30m & 5m)")
    except Exception as e:
        print(f"❌ Lab Table Init Error: {e}")
    finally:
        conn.close()

def bulk_insert_lab_data(table_name, data_list):
    """
    Bulk insert data into specified table.
    data_list: List of tuples (ticker, candle_time, open, high, low, close, volume, ma10, ma30, change_pct)
    Uses INSERT IGNORE to skip duplicates.
    """
    if not data_list: return 0, 0
    
    conn = get_connection()
    inserted_count = 0
    
    try:
        with conn.cursor() as cursor:
            # Construct query
            # We use ON DUPLICATE KEY UPDATE to ensure latest data wins, or INSERT IGNORE?
            # User said: "Check duplicates and fill in missing ones".
            # Usually users might upload corrected data, so ON DUPLICATE KEY UPDATE might be better?
            # But let's stick to safe INSERT IGNORE or ON DUPLICATE KEY UPDATE.
            # Let's use ON DUPLICATE KEY UPDATE for robustness (latest upload overwrites).
            
            sql = f"""
                INSERT INTO {table_name} 
                (ticker, candle_time, open, high, low, close, volume, ma10, ma30, change_pct)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                open=VALUES(open), high=VALUES(high), low=VALUES(low), close=VALUES(close),
                volume=VALUES(volume), ma10=VALUES(ma10), ma30=VALUES(ma30), change_pct=VALUES(change_pct)
            """
            
            result = cursor.executemany(sql, data_list)
            conn.commit()
            inserted_count = result # executemany result might be confusing with ON DUPLICATE (returns 2 for update)
            # But roughly it indicates success.
            # Actually, return len(data_list) is safer if no exception.
            inserted_count = len(data_list)
            
    except Exception as e:
        print(f"❌ Bulk Insert Error ({table_name}): {e}")
        raise e
    finally:
        conn.close()
        
    return inserted_count

def bulk_update_scores(table_name, update_list):
    """
    Bulk update scores for existing rows.
    update_list: List of dicts or tuples containing (id, scores...)
    We use UPDATE based on ID for speed, or Ticker+Time.
    Assuming we fetch IDs first, updating by ID is fastest.
    
    Data format: (total_score, s_c1, s_c2, s_c3, s_en, s_atr, s_bbi, s_rsi, s_macd, s_vol, algo_ver, calc_at, id)
    """
    if not update_list: return 0
    
    conn = get_connection()
    updated_count = 0
    try:
        with conn.cursor() as cursor:
            # Prepare SQL
            sql = f"""
                UPDATE {table_name}
                SET 
                    total_score=%s,
                    score_cheongan_1=%s, score_cheongan_2=%s, score_cheongan_3=%s,
                    score_energy=%s, score_atr=%s, score_bbi=%s,
                    score_rsi=%s, score_macd=%s, score_vol=%s, score_slope=%s,
                    algo_version=%s, calculated_at=%s,
                    change_pct=%s
                WHERE id=%s
            """
            
            # Execute Batch
            # Check batch size? If too large, split?
            # 1000 at a time is safe.
            batch_size = 1000
            for i in range(0, len(update_list), batch_size):
                batch = update_list[i : i + batch_size]
                cursor.executemany(sql, batch)
                updated_count += len(batch)
            
            conn.commit()
    except Exception as e:
        print(f"❌ Bulk Update Error ({table_name}): {e}")
        raise e
    finally:
        conn.close()
        
    return updated_count

def save_realtime_lab_data(data_list):
    """
    [User Request] Save Real-time Action Plan Scores to lab_data_5m (Algo Version)
    data_list: List of dicts {
        ticker, candle_time (US), open, high, low, close, volume, 
        ma10, ma30, change_pct, 
        scores: {total, sig1, sig2, sig3, energy, atr, bbi, rsi, macd, vol}
    }
    """
    if not data_list: return 0
    
    conn = get_connection()
    inserted_count = 0
    
    try:
        with conn.cursor() as cursor:
            # Prepare SQL for lab_data_5m
            sql = """
                INSERT INTO lab_data_5m 
                (ticker, candle_time, open, high, low, close, volume, ma10, ma30, change_pct,
                 total_score, score_cheongan_1, score_cheongan_2, score_cheongan_3,
                 score_energy, score_atr, score_bbi, score_rsi, score_macd, score_vol, score_slope,
                 algo_version, calculated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s,
                        'true', NOW())
                ON DUPLICATE KEY UPDATE
                open=VALUES(open), high=VALUES(high), low=VALUES(low), close=VALUES(close),
                volume=VALUES(volume), ma10=VALUES(ma10), ma30=VALUES(ma30), change_pct=VALUES(change_pct),
                total_score=VALUES(total_score),
                score_cheongan_1=VALUES(score_cheongan_1), score_cheongan_2=VALUES(score_cheongan_2), score_cheongan_3=VALUES(score_cheongan_3),
                score_energy=VALUES(score_energy), score_atr=VALUES(score_atr), score_bbi=VALUES(score_bbi),
                score_rsi=VALUES(score_rsi), score_macd=VALUES(score_macd), score_vol=VALUES(score_vol), 
                score_slope=VALUES(score_slope),
                algo_version='true', calculated_at=NOW()
            """
            
            params = []
            for item in data_list:
                scores = item.get('scores', {})
                params.append((
                    item['ticker'], item['candle_time'], 
                    item.get('open', 0), item.get('high', 0), item.get('low', 0), item['close'], item.get('volume', 0),
                    item.get('ma10', 0), item.get('ma30', 0), item.get('change_pct', 0),
                    scores.get('total', 0),
                    scores.get('sig1', 0), scores.get('sig2', 0), scores.get('sig3', 0),
                    scores.get('energy', 0), scores.get('atr', 0), scores.get('bbi', 0),
                    scores.get('rsi', 0), scores.get('macd', 0), scores.get('vol', 0),
                    scores.get('slope', 0)
                ))
            
            if params:
                cursor.executemany(sql, params)
                conn.commit()
                inserted_count = len(params)
                print(f"✅ Real-time Lab Data Saved: {inserted_count} rows")
            
    except Exception as e:
        print(f"❌ Save Realtime Lab Data Error: {e}")
    finally:
        conn.close()
        
    return inserted_count

def get_last_lab_data(ticker):
    """
    [v9.6.6] Fetch the latest valid record (Price > 0) for Fallback.
    Returns dict or None.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Get latest 5m data where close > 0
            sql = """
                SELECT open, high, low, close, volume, ma10, ma30, change_pct,
                       total_score, score_cheongan_1, score_cheongan_2, score_cheongan_3,
                       score_energy, score_atr, score_bbi, score_rsi, score_macd, score_vol, score_slope
                FROM lab_data_5m
                WHERE ticker = %s AND close > 0
                ORDER BY candle_time DESC
                LIMIT 1
            """
            cursor.execute(sql, (ticker,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'open': float(row[0]), 'high': float(row[1]), 'low': float(row[2]), 'close': float(row[3]),
                    'volume': int(row[4]),
                    'ma10': float(row[5]), 'ma30': float(row[6]), 'change_pct': float(row[7]),
                    'scores': {
                        'total': int(row[8]),
                        'sig1': int(row[9]), 'sig2': int(row[10]), 'sig3': int(row[11]),
                        'energy': int(row[12]), 'atr': int(row[13]), 'bbi': int(row[14]),
                        'rsi': int(row[15]), 'macd': int(row[16]), 'vol': int(row[17]), 'slope': float(row[18])
                    }
                }
            return None
    except Exception as e:
        print(f"❌ Get Last Lab Data Error ({ticker}): {e}")
        return None
    finally:
        conn.close()
