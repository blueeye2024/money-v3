
import pymysql
from db import get_connection

def init_sim_tables():
    """Create sim_data_5m table if not exist."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 5m Table for Simulator
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sim_data_5m (
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
            conn.commit()
    finally:
        conn.close()

def clear_sim_data():
    """Truncate simulator table before new run."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE sim_data_5m")
            conn.commit()
    finally:
        conn.close()

def bulk_insert_sim_data(data_list):
    """
    Bulk insert raw candle data into sim_data_5m.
    data_list: list of tuples (ticker, candle_time, open, high, low, close, volume, change_pct)
    """
    if not data_list: return 0
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Only insert raw data, scores are calculated later
            sql = """
                INSERT IGNORE INTO sim_data_5m 
                (ticker, candle_time, open, high, low, close, volume, change_pct)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.executemany(sql, data_list)
            inserted = cursor.rowcount
            conn.commit()
            return inserted
    except Exception as e:
        print(f"Bulk Insert Error (Sim): {e}")
        return 0
    finally:
        conn.close()

def bulk_update_sim_scores(updates):
    """
    Bulk update calculated scores.
    updates: list of tuples (total, sc1, sc2, sc3, en, atr, bbi, rsi, macd, vol, algo, calc_at, change_pct, row_id)
    """
    if not updates: return 0
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                UPDATE sim_data_5m
                SET 
                    total_score=%s, 
                    score_cheongan_1=%s, score_cheongan_2=%s, score_cheongan_3=%s,
                    score_energy=%s, score_atr=%s, score_bbi=%s, score_rsi=%s, score_macd=%s, score_vol=%s,
                    algo_version=%s, calculated_at=%s, change_pct=%s
                WHERE id=%s
            """
            cursor.executemany(sql, updates)
            updated = cursor.rowcount
            conn.commit()
            return updated
    except Exception as e:
        print(f"Bulk Update Error (Sim): {e}")
        return 0
    finally:
        conn.close()
