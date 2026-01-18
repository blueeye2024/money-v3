import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB
import os
from datetime import datetime

# Connection Config
DB_CONFIG = {
    "host": "114.108.180.228",
    "port": 3306,
    "user": "blueeye",
    "password": "blueeye0037!",
    "database": "mywork_01",
    "charset": "utf8mb4",
    "cursorclass": DictCursor
}

# Connection Pool (prevents "Too many open files" error)
_connection_pool = None

def _get_pool():
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = PooledDB(
                creator=pymysql,
                maxconnections=10,  # Maximum connections
                mincached=2,        # Minimum idle connections in pool
                maxcached=5,        # Maximum idle connections in pool
                maxusage=None,      # Number of times a connection can be reused
                blocking=True,      # Block if pool is full
                ping=1,             # Check connection before using (0=never, 1=default, 2=when checked out, 4=when checked in, 7=always)
                **DB_CONFIG
            )
        except Exception as e:
            print(f"Connection Pool Creation Error: {e}")
            # Fallback to direct connection
            return None
    return _connection_pool


def save_market_snapshot(data):
    """
    시장 지표 스냅샷 저장 (Latest State Only)
    Update the market_indicators_snapshot table.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO market_indicators_snapshot 
            (ticker, candle_time, rsi_14, vol_ratio, atr, pivot_r1, macd, macd_sig, gold_30m, gold_5m, dead_30m, dead_5m, score, evaluation, strategy_comment, v2_state)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                candle_time=VALUES(candle_time),
                rsi_14=VALUES(rsi_14),
                vol_ratio=VALUES(vol_ratio),
                atr=VALUES(atr),
                pivot_r1=VALUES(pivot_r1),
                macd=VALUES(macd),
                macd_sig=VALUES(macd_sig),
                gold_30m=VALUES(gold_30m),
                gold_5m=VALUES(gold_5m),
                dead_30m=VALUES(dead_30m),
                dead_5m=VALUES(dead_5m),
                score=VALUES(score),
                evaluation=VALUES(evaluation),
                strategy_comment=VALUES(strategy_comment),
                v2_state=VALUES(v2_state),
                updated_at=CURRENT_TIMESTAMP
            """
            cursor.execute(sql, (
                data['ticker'], data['candle_time'], 
                data.get('rsi', 0), data.get('vr', 0), data.get('atr', 0), data.get('pivot_r1', 0),
                data.get('macd', 0), data.get('macd_sig', 0),
                data.get('gold_30m', 'N'), data.get('gold_5m', 'N'),
                data.get('dead_30m', 'N'), data.get('dead_5m', 'N'),
                data.get('score', 0), data.get('evaluation', ''), 
                data.get('comment', ''), data.get('v2_state', '')
            ))
            conn.commit()
    except Exception as e:
        print(f"Save Snapshot Error: {e}")
    finally:
        conn.close()

def log_market_history(data):
    """
    시장 지표 히스토리 저장 (Append)
    Insert into market_indicators_history table.
    [Updated] Saves only if > 10 minutes have passed since last log for this ticker.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Check last save time
            cursor.execute("SELECT created_at FROM market_indicators_history WHERE ticker=%s ORDER BY id DESC LIMIT 1", (data['ticker'],))
            last_row = cursor.fetchone()
            
            should_save = True
            if last_row:
                last_time = last_row.get('created_at') # datetime object
                if last_time:
                    # Calculate diff
                    now = datetime.now() # Server time (assuming DB time is close or convert)
                    # DB created_at is likely Naive or Server Local. 
                    # Let's rely on DB time diff to be safe? Or simple python diff.
                    # Assuming running on same machine/timezone setup.
                    diff = (now - last_time).total_seconds() / 60.0
                    if diff < 10:
                        should_save = False
                        # print(f"Skipping History Log for {data['ticker']} (Last: {diff:.1f}m ago)")

            if should_save:
                sql = """
                INSERT INTO market_indicators_history 
                (ticker, candle_time, rsi_14, vol_ratio, atr, pivot_r1, macd, macd_sig, gold_30m, gold_5m, dead_30m, dead_5m, score, evaluation, strategy_comment, v2_state)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    data['ticker'], data['candle_time'], 
                    data.get('rsi', 0), data.get('vr', 0), data.get('atr', 0), data.get('pivot_r1', 0),
                    data.get('macd', 0), data.get('macd_sig', 0),
                    data.get('gold_30m', 'N'), data.get('gold_5m', 'N'),
                    data.get('dead_30m', 'N'), data.get('dead_5m', 'N'),
                    data.get('score', 0), data.get('evaluation', ''), 
                    data.get('comment', ''), data.get('v2_state', '')
                ))
                conn.commit()
                # print(f"History Log Saved for {data['ticker']}")
    except Exception as e:
        print(f"Log History Error: {e}")
    finally:
        conn.close()

def get_connection():
    """Get database connection from pool (with context manager support)"""
    pool = _get_pool()
    if pool:
        try:
            return pool.connection()
        except Exception as e:
            print(f"Pool Connection Error: {e}")
            # Fallback to direct connection
            return pymysql.connect(**DB_CONFIG)
    else:
        # Direct connection fallback
        return pymysql.connect(**DB_CONFIG)

def init_db():
    """Initialize tables if they don't exist"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Signals Table (Auto-detected signals)
            sql_signals = """
            CREATE TABLE IF NOT EXISTS signal_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10) NOT NULL,
                name VARCHAR(100),
                signal_type VARCHAR(50), 
                position_desc VARCHAR(255),
                price DECIMAL(10, 2),
                signal_time DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_sent BOOLEAN DEFAULT FALSE
            )
            """
            cursor.execute(sql_signals)
            

            # 2. Stocks Table (Master Data)
            # [Updated Ver 6.5] Added is_active column
            sql_stocks = """
            CREATE TABLE IF NOT EXISTS stocks (
                code VARCHAR(10) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql_stocks)
            
            # Migration: Ensure is_active column exists if table already existed
            try:
                cursor.execute("DESCRIBE stocks")
                cols = [row['Field'] for row in cursor.fetchall()]
                if 'is_active' not in cols:
                    cursor.execute("ALTER TABLE stocks ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
            except Exception as e:
                print(f"Migration add column error: {e}")

            # Migration: Sync from managed_stocks to stocks (One-time)
            # Insert any missing stocks from managed_stocks into stocks
            try:
                cursor.execute("""
                    INSERT IGNORE INTO stocks (code, name, is_active)
                    SELECT ticker, name, is_active FROM managed_stocks
                """)
                conn.commit()
            except Exception as e:
                 print(f"Migration sync error: {e}")


            # 3. Journal Transactions Table (Ledger Style)
            sql_journal = """
            CREATE TABLE IF NOT EXISTS journal_transactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10) NOT NULL,
                trade_type VARCHAR(10) NOT NULL, -- BUY or SELL
                qty INT DEFAULT 1,
                price DECIMAL(15, 2) NOT NULL,
                trade_date DATETIME NOT NULL,
                memo TEXT,
                category VARCHAR(20) DEFAULT '기타',
                group_name VARCHAR(50) DEFAULT '',
                expected_sell_date DATE,
                target_sell_price DECIMAL(15, 2),
                strategy_memo TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql_journal)
            
            # Migration: Add group_name, category to journal_transactions if missing
            try:
                cursor.execute("DESCRIBE journal_transactions")
                cols = [row['Field'] for row in cursor.fetchall()]
                if 'group_name' not in cols:
                    cursor.execute("ALTER TABLE journal_transactions ADD COLUMN group_name VARCHAR(50) DEFAULT ''")
                if 'category' not in cols:
                    cursor.execute("ALTER TABLE journal_transactions ADD COLUMN category VARCHAR(20) DEFAULT '기타'")
            except Exception as e:
                print(f"Migration journal schema error: {e}")

            # 4. Market Candles Table (Historical Data)
            sql_candles = """
            CREATE TABLE IF NOT EXISTS market_candles (
                ticker VARCHAR(10) NOT NULL,
                timeframe VARCHAR(10) NOT NULL, -- 30m, 5m, 1d
                candle_time DATETIME NOT NULL,
                open_price DECIMAL(12, 4),
                high_price DECIMAL(12, 4),
                low_price DECIMAL(12, 4),
                close_price DECIMAL(12, 4),
                volume BIGINT,
                source VARCHAR(20), -- yfinance, kis
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (ticker, timeframe, candle_time)
            )
            """
            cursor.execute(sql_candles)

            # 4. SMS Logs Table
            sql_sms_logs = """
            CREATE TABLE IF NOT EXISTS sms_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                receiver VARCHAR(20),
                message TEXT,
                status VARCHAR(20),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql_sms_logs)

            # 5. Ticker Settings (Dashboard Visibility)
            sql_ticker_settings = """
            CREATE TABLE IF NOT EXISTS ticker_settings (
                ticker VARCHAR(10) PRIMARY KEY,
                is_visible BOOLEAN DEFAULT TRUE,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql_ticker_settings)
            
            # 6. Market Indices (S&P500, NASDAQ, GOLD, KRW)
            sql_indices = """
            CREATE TABLE IF NOT EXISTS market_indices (
                ticker VARCHAR(20) PRIMARY KEY,
                name VARCHAR(50),
                current_price DECIMAL(10, 2),
                change_pct DECIMAL(5, 2),
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql_indices)

            # 7. SOXS Specific Candle Data (User Custom Table)
            sql_soxs = """
            CREATE TABLE IF NOT EXISTS soxs_candle_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                seq INT COMMENT '순번',
                candle_date DATE COMMENT '일자',
                is_30m CHAR(1) COMMENT '30분봉 사용 (Y)',
                hour INT COMMENT '시간',
                minute INT COMMENT '분',
                close_price DECIMAL(10, 4) COMMENT '종가 가격',
                volume BIGINT COMMENT '거래량',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '업데이트 시간',
                source VARCHAR(50) COMMENT '출처'
            )
            """
            cursor.execute(sql_soxs)

            # 8. SOXL Specific Candle Data (User Custom Table)
            sql_soxl = """
            CREATE TABLE IF NOT EXISTS soxl_candle_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                seq INT COMMENT '순번',
                candle_date DATE COMMENT '일자',
                is_30m CHAR(1) COMMENT '30분봉 사용 (Y)',
                hour INT COMMENT '시간',
                minute INT COMMENT '분',
                close_price DECIMAL(10, 4) COMMENT '종가 가격',
                volume BIGINT COMMENT '거래량',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '업데이트 시간',
                source VARCHAR(50) COMMENT '출처'
            )
            """
            cursor.execute(sql_soxl)

            # 9. UPRO Specific Candle Data (User Custom Table)
            sql_upro = """
            CREATE TABLE IF NOT EXISTS upro_candle_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                seq INT COMMENT '순번',
                candle_date DATE COMMENT '일자',
                is_30m CHAR(1) COMMENT '30분봉 사용 (Y)',
                hour INT COMMENT '시간',
                minute INT COMMENT '분',
                close_price DECIMAL(10, 4) COMMENT '종가 가격',
                volume BIGINT COMMENT '거래량',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '업데이트 시간',
                source VARCHAR(50) COMMENT '출처'
            )
            """
            cursor.execute(sql_upro)

            # 10. Market Indicators Log (Analysis History)
            sql_indicators = """
            CREATE TABLE IF NOT EXISTS market_indicators_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10) NOT NULL,
                candle_time DATETIME NOT NULL COMMENT '기준 캔들 시간(NY)',
                rsi_14 DECIMAL(10, 2),
                vol_ratio DECIMAL(10, 2),
                atr DECIMAL(10, 4),
                pivot_r1 DECIMAL(10, 2),
                gold_30m VARCHAR(30) DEFAULT 'N' COMMENT '30분 골든 발생시간(KR) or N',
                gold_5m VARCHAR(30) DEFAULT 'N' COMMENT '5분 골든 발생시간(KR) or N',
                dead_30m VARCHAR(30) DEFAULT 'N' COMMENT '30분 데드 발생시간(KR) or N',
                dead_5m VARCHAR(30) DEFAULT 'N' COMMENT '5분 데드 발생시간(KR) or N',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '분석 실행 시간(Log Time)'
            )
            """
            cursor.execute(sql_indicators)





            # 6. Auto Trade History (Simulated)
            sql_trade = """
            CREATE TABLE IF NOT EXISTS trade_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10) NOT NULL,
                entry_time DATETIME NOT NULL,
                entry_price DECIMAL(10, 4),
                exit_time DATETIME,
                exit_price DECIMAL(10, 4),
                profit_pct DECIMAL(10, 2),
                status VARCHAR(20) DEFAULT 'OPEN', -- OPEN, CLOSED
                strategy_ver VARCHAR(20),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql_trade)
            
            # 6. Cheongan 2.0: Market Status (Regime)
            sql_market = """
            CREATE TABLE IF NOT EXISTS market_status (
                date DATE PRIMARY KEY,
                regime VARCHAR(20), -- Bull, Bear, Sideways
                details JSON,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql_market)

            # 7. Cheongan 2.0: Managed Stocks (Core Trading List)
            sql_managed = """
            CREATE TABLE IF NOT EXISTS managed_stocks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10) UNIQUE,
                name VARCHAR(100),
                group_name VARCHAR(50), -- Group 1, 2, 3
                buy_strategy TEXT,
                sell_strategy TEXT,
                target_ratio INT DEFAULT 0, -- Portfolio weight %
                scenario_yield DECIMAL(5,2) DEFAULT 0.0,
                real_yield DECIMAL(5,2) DEFAULT 0.0,
                win_rate DECIMAL(5,2) DEFAULT 0.0,
                memo TEXT,
                version VARCHAR(20) DEFAULT '2.0',
                is_active BOOLEAN DEFAULT TRUE,
                current_price DECIMAL(10,2) DEFAULT 0.0,
                price_updated_at DATETIME DEFAULT NULL,
                is_market_open BOOLEAN DEFAULT TRUE,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql_managed)

            # 8. Cheongan 2.0: Global Config (Safety Switch & Rules)
            sql_config = """
            CREATE TABLE IF NOT EXISTS global_config (
                key_name VARCHAR(50) PRIMARY KEY,
                value_json JSON,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql_config)

            # 9. User Requests Tracking
            sql_requests = """
            CREATE TABLE IF NOT EXISTS user_requests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                request_text TEXT,
                ai_interpretation TEXT,
                implementation_details TEXT,
                status VARCHAR(20) DEFAULT 'completed',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql_requests)

            # 10. Price Cache (KIS API Data Storage)
            sql_price_cache = """
            CREATE TABLE IF NOT EXISTS price_cache (
                ticker VARCHAR(10) PRIMARY KEY,
                price DECIMAL(10,4),
                diff DECIMAL(10,4),
                rate DECIMAL(6,3),
                exchange VARCHAR(10),
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql_price_cache)

            # 11. Candle Data Cache (5m/30m Snapshots for Holiday/Fallback)
            sql_candle = """
            CREATE TABLE IF NOT EXISTS candle_data (
                ticker VARCHAR(10),
                timeframe VARCHAR(5), -- '5m' or '30m'
                candle_time DATETIME,
                open DECIMAL(10,4),
                high DECIMAL(10,4),
                low DECIMAL(10,4),
                close DECIMAL(10,4),
                volume BIGINT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (ticker, timeframe, candle_time),
                INDEX idx_ticker_timeframe (ticker, timeframe),
                INDEX idx_candle_time (candle_time)
            )
            """
            cursor.execute(sql_candle)

            # 12. Cheongan V2: Signal Monitoring (buy_stock)
            sql_buy = """
            CREATE TABLE IF NOT EXISTS buy_stock (
                idx INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10) NOT NULL,
                manage_id VARCHAR(30) NOT NULL UNIQUE,
                current_price DECIMAL(18,6),
                row_dt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                buy_sig1_yn CHAR(1) DEFAULT 'N',
                buy_sig2_yn CHAR(1) DEFAULT 'N',
                buy_sig3_yn CHAR(1) DEFAULT 'N',
                buy_sig1_dt DATETIME,
                buy_sig2_dt DATETIME,
                buy_sig3_dt DATETIME,
                buy_sig1_price DECIMAL(18,6),
                buy_sig2_price DECIMAL(18,6),
                buy_sig3_price DECIMAL(18,6),
                final_buy_yn CHAR(1) DEFAULT 'N',
                final_buy_dt DATETIME,
                final_buy_price DECIMAL(18,6),
                real_buy_yn CHAR(1) DEFAULT 'N',
                real_buy_price DECIMAL(18,6),
                real_buy_qn DECIMAL(10,2),
                real_buy_dt DATETIME
            )
            """
            cursor.execute(sql_buy)

            # 13. Cheongan V2: Position Management (sell_stock)
            sql_sell = """
            CREATE TABLE IF NOT EXISTS sell_stock (
                idx INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10) NOT NULL,
                manage_id VARCHAR(30) NOT NULL UNIQUE,
                current_price DECIMAL(18,6),
                row_dt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                sell_sig1_yn CHAR(1) DEFAULT 'N',
                sell_sig2_yn CHAR(1) DEFAULT 'N',
                sell_sig3_yn CHAR(1) DEFAULT 'N',
                sell_sig1_dt DATETIME,
                sell_sig2_dt DATETIME,
                sell_sig3_dt DATETIME,
                sell_sig1_price DECIMAL(18,6),
                sell_sig2_price DECIMAL(18,6),
                sell_sig3_price DECIMAL(18,6),
                sell_ratio1 DECIMAL(5,2),
                sell_ratio2 DECIMAL(5,2),
                sell_ratio3 DECIMAL(5,2),
                final_sell_yn CHAR(1) DEFAULT 'N',
                final_sell_dt DATETIME,
                final_sell_price DECIMAL(18,6),
                real_hold_yn CHAR(1) DEFAULT 'N',
                real_sell_avg_price DECIMAL(18,6),
                real_sell_qn DECIMAL(10,2),
                real_sell_dt DATETIME,
                close_yn CHAR(1) DEFAULT 'N'
            )
            """
            cursor.execute(sql_sell)

            # 14. Cheongan V2: History (history)
            sql_history = """
            CREATE TABLE IF NOT EXISTS history (
                idx INT AUTO_INCREMENT PRIMARY KEY,
                log_dt DATETIME DEFAULT CURRENT_TIMESTAMP,
                ticker VARCHAR(10) NOT NULL,
                manage_id VARCHAR(30) NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                event_dt DATETIME,
                event_price DECIMAL(18,6),
                short_msg VARCHAR(200),
                sms_sent_yn CHAR(1) DEFAULT 'N',
                INDEX idx_manage_time (manage_id, event_dt),
                INDEX idx_ticker_time (ticker, event_dt)
            )
            """
            cursor.execute(sql_history)

            # 12. System Auto-Trading Log
            sql_sys_trade = """
            CREATE TABLE IF NOT EXISTS system_trades (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10) NOT NULL,
                trade_type VARCHAR(10) NOT NULL, -- BUY or SELL
                price DECIMAL(10, 4) NOT NULL,
                qty DECIMAL(10, 4) DEFAULT 1,
                trade_time DATETIME NOT NULL,
                profit_pct DECIMAL(6, 2) DEFAULT NULL, -- Only for SELL
                realized_pl DECIMAL(10, 2) DEFAULT NULL, -- Only for SELL
                strategy_note VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql_sys_trade)

            # 15. Trading Journal (거래일지)
            sql_trade_journal = """
            CREATE TABLE IF NOT EXISTS trade_journal (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(20) NOT NULL,
                -- 매수 정보
                buy_date DATETIME,
                buy_price DECIMAL(10,4),
                buy_qty INT DEFAULT 1,
                buy_reason TEXT,
                -- 매도 정보
                sell_date DATETIME,
                sell_price DECIMAL(10,4),
                sell_qty INT,
                sell_reason TEXT,
                -- 분석 필드
                market_condition VARCHAR(50),
                emotion_before VARCHAR(20),
                emotion_after VARCHAR(20),
                score_at_entry INT,
                score_at_exit INT,
                -- 결과
                realized_pnl DECIMAL(10,2),
                realized_pnl_pct DECIMAL(5,2),
                hold_days INT,
                lesson TEXT,
                tags VARCHAR(255),
                screenshot LONGTEXT,
                -- 메타
                status ENUM('OPEN','CLOSED') DEFAULT 'OPEN',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_ticker (ticker),
                INDEX idx_status (status),
                INDEX idx_buy_date (buy_date)
            )
            """
            cursor.execute(sql_trade_journal)

            # 16. Daily Reports (Ver 5.8)
            sql_daily_reports = """
            CREATE TABLE IF NOT EXISTS daily_reports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                report_date DATE UNIQUE NOT NULL,
                pre_market_strategy TEXT,
                post_market_memo TEXT,
                profit_rate FLOAT,
                profit_amount DECIMAL(15, 2),
                prev_total_asset DECIMAL(15, 2),
                image_paths TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql_daily_reports)

            # 17. Market Events / Calendar (Ver 5.8)
            sql_market_events = """
            CREATE TABLE IF NOT EXISTS market_events (
                id INT AUTO_INCREMENT PRIMARY KEY,
                event_date DATE NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                importance ENUM('HIGH', 'MEDIUM', 'LOW') DEFAULT 'MEDIUM',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql_market_events)

            # --- Seed Initial Data ---
            # Seed Managed Stocks
            # Seed Global Config (Rules)
            import json
            rules = {
                "box_days": 7,
                "box_range_pct_base": 5.0,
                "volume_threshold_pct": 120,
                "safety_drawdown_limit": -10.0,
                "version": "2.0.0"
            }
            cursor.execute("INSERT INTO global_config (key_name, value_json) VALUES (%s, %s) ON DUPLICATE KEY UPDATE value_json=VALUES(value_json)", ('common_rules', json.dumps(rules)))


            
        conn.commit()
    except Exception as e:
        print(f"DB Initialization Error: {e}")
    finally:
        conn.close()


def add_user_request(request_text, interpretation, details):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO user_requests (request_text, ai_interpretation, implementation_details) VALUES (%s, %s, %s)"
            cursor.execute(sql, (request_text, interpretation, details))
        conn.commit()
        return True
    finally:
        conn.close()

def get_user_requests():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM user_requests ORDER BY created_at DESC")
            return cursor.fetchall()
    finally:
        conn.close()


def save_signal(signal_data):
    """Save a detected signal to DB"""
    conn = get_connection()
    try:
        # Convert pandas Timestamp to python datetime if needed
        st = signal_data['signal_time_raw']
        if hasattr(st, 'to_pydatetime'):
            st = st.to_pydatetime()
            
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO signal_history (ticker, name, signal_type, signal_reason, position_desc, price, signal_time, time_kst, time_ny, is_sent, score, interpretation)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                signal_data['ticker'],
                signal_data['name'],
                signal_data['signal_type'],
                signal_data.get('signal_reason', ''),  # 신호 발생 이유
                signal_data['position'],
                signal_data['current_price'],
                st, 
                signal_data.get('time_kst', ''),  # 한국시간
                signal_data.get('time_ny', ''),   # 미국시간
                signal_data.get('is_sent', False),
                signal_data.get('score', 0),
                signal_data.get('interpretation', '')
            ))
        conn.commit()
    except Exception as e:
        print(f"Save Signal Error: {e}")
        # Re-raise to ensure calling logic knows it failed, or handle gracefully?
        # If we silence it, SMS might send but DB empty. Let's print and pass for now to allow SMS to proceed if DB is flaky, 
        # BUT user complained about missing history. Let's log heavily.
    finally:
        conn.close()

def check_last_signal(ticker):
    """Get the last saved signal for a ticker to prevent duplicates"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM signal_history WHERE ticker=%s ORDER BY signal_time DESC LIMIT 1"
            cursor.execute(sql, (ticker,))
            return cursor.fetchone()
    finally:
        conn.close()

def get_signals(ticker=None, start_date=None, end_date=None, limit=30):
    """Fetch signal history with filtering"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM signal_history WHERE 1=1"
            params = []
            if ticker and ticker.strip() != "":
                sql += " AND ticker = %s"
                params.append(ticker)
            if start_date:
                sql += " AND signal_time >= %s"
                params.append(f"{start_date} 00:00:00")
            if end_date:
                sql += " AND signal_time <= %s"
                params.append(f"{end_date} 23:59:59")
            
            sql += " ORDER BY signal_time DESC LIMIT %s"
            params.append(int(limit))
            
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        conn.close()

def delete_signal(id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM signal_history WHERE id=%s", (id,))
        conn.commit()
        return True
    finally:
        conn.close()

def delete_all_signals():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM signal_history")
        conn.commit()
        return True
    finally:
        conn.close()

def save_sms_log(receiver, message, status):
    """Save SMS send log"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO sms_logs (receiver, message, status) VALUES (%s, %s, %s)"
            cursor.execute(sql, (receiver, message, status))
        conn.commit()
    finally:
        conn.close()

def get_sms_logs(limit=30):
    """Fetch recent SMS logs"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM sms_logs ORDER BY created_at DESC LIMIT %s"
            cursor.execute(sql, (int(limit),))
            return cursor.fetchall()
    finally:
        conn.close()

def delete_sms_log(id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM sms_logs WHERE id=%s", (id,))
        conn.commit()
        return True
    finally:
        conn.close()

def delete_all_sms_logs():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM sms_logs")
        conn.commit()
        return True
    finally:
        conn.close()

def check_recent_sms_log(stock_name, signal_type, timeframe_minutes=30):
    """Check if a similar SMS was sent recently"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check for messages containing the stock name AND signal type within timeframe
            # Note: signal_type from logic ('매수 진입' etc) might differ slightly from message format, but usually consistent.
            # Message format: [...][stock_name][signal_type]...
            
            # Using LIKE query
            sql = """
            SELECT id, created_at FROM sms_logs 
            WHERE message LIKE %s AND message LIKE %s 
            AND created_at >= NOW() - INTERVAL %s MINUTE
            LIMIT 1
            """
            # Add brackets to match exact format in SMS function
            like_stock = f"%[{stock_name}]%"
            # Simplify signal type matching (e.g. just "매수" or "매도") to catch broader duplicates? 
            # User said: "Same stock and status(buy/sell)". 
            # 'signal_type' passed here is usually '매수 진입' or 'box_upper'.
            # Let's use the exact string passed to the SMS function logic.
            like_type = f"%[{signal_type}]%"
            
            cursor.execute(sql, (like_stock, like_type, int(timeframe_minutes)))
            return cursor.fetchone()
    finally:
        conn.close()



# --- Stock Management ---
def get_stocks():
    """종목 목록 조회 (Master List from active `stocks` table)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # [Updated Ver 6.5] Use `stocks` table as master
            cursor.execute("""
                SELECT code, name, is_active
                FROM stocks 
                ORDER BY code ASC
            """)
            rows = cursor.fetchall()
            return rows
    except Exception as e:
        print(f"Get Stocks Error: {e}")
        return []
    finally:
        conn.close()

def add_stock(code, name, is_active=True):
    """종목 추가 (Master List)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Insert into stocks (Master)
            sql = """
            INSERT INTO stocks (code, name, is_active) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE name=VALUES(name), is_active=VALUES(is_active)
            """
            cursor.execute(sql, (code, name, is_active))
            
            # 2. Also ensure it exists in managed_stocks for legacy compatibility (optional but safe)
            # Only if it doesn't exist? Or just leave it to be created when transaction happens?
            # User wants to separate them. But if we add to Master, it doesn't necessarily mean we have holdings.
            # So we do NOT add to managed_stocks automatically unless user inputs transaction.
            pass

        conn.commit()
        return True
    except Exception as e:
        print(f"Add Stock Error: {e}")
        return False
    finally:
        conn.close()

def update_stock_status(code, is_active):
    """종목 상태 변경 (Master List)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE stocks SET is_active=%s WHERE code=%s", (is_active, code))
            # Also sync managed_stocks active status if it exists, to keep UI consistent?
            # Let's keep them in sync for now if the column exists there too.
            cursor.execute("UPDATE managed_stocks SET is_active=%s WHERE ticker=%s", (is_active, code))
        conn.commit()
        return True
    except Exception as e:
        print(f"Update Stock Status Error: {e}")
        return False
    finally:
        conn.close()

def delete_stock(code):
    """종목 삭제 (Master List) - Cascade implies risks, so be careful"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # User request: "If holding deleted, code shouldn't be deleted."
            # Here: "If Master Code deleted, what happens?"
            # Usually Master Delete should block if holdings exist OR cascade delete everything.
            # Given user wants to manage them separately, Master Delete means "I don't want this stock in my system anymore".
            # So we delete from stocks. 
            
            # Check if active holdings exist?
            cursor.execute("SELECT quantity FROM managed_stocks WHERE ticker=%s AND quantity > 0", (code,))
            row = cursor.fetchone()
            if row:
                # If active holdings exist, strictly maybe we shouldn't delete master?
                # But user can delete if they really want to.
                # Let's clean up everything.
                pass

            cursor.execute("DELETE FROM stocks WHERE code=%s", (code,))
            # managed_stocks will NOT be automatically deleted unless we defined FK cascade manually or in DB.
            # In init_db, managed_stocks table definition (lines 200+) did NOT show FK. 
            # I should explicitly delete from managed_stocks if we want to clean up.
            cursor.execute("DELETE FROM managed_stocks WHERE ticker=%s", (code,))
            
        conn.commit()
        return True
    except Exception as e:
        print(f"Delete Stock Error: {e}")
        return False
    finally:
        conn.close()

# --- Journal Transactions ---
# Transaction Functions (Refactored to Holdings)
# add_transaction removed as journal_transactions table is dropped.
# Use update_holding instead.

# 3. Journal Transactions (Merged into managed_stocks, table dropped)
            # sql_journal = ... (Deleted)

def get_holdings():
    """자산 보유 현황 조회 (From managed_stocks)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # managed_stocks에서 수량, 평단가, 현재가 모두 조회
            sql = """
            SELECT ticker, name, quantity as qty, avg_price, current_price, is_market_open, is_manual_price,
                   category, group_name, is_holding, expected_sell_date, target_sell_price, strategy_memo
            FROM managed_stocks 
            ORDER BY ticker ASC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            # Convert Decimal/Datetime for JSON safety
            cleaned = []
            for r in rows:
                row = dict(r)
                for k, v in row.items():
                    import decimal
                    from datetime import datetime
                    if isinstance(v, decimal.Decimal):
                        row[k] = float(v)
                    elif isinstance(v, datetime):
                        row[k] = v.strftime('%Y-%m-%d %H:%M:%S')
                cleaned.append(row)
            return cleaned

    except Exception as e:
        print(f"Get Holdings Error: {e}")
        return []
    finally:
        conn.close()


# Legacy update_holding removed - using v6.2 version with category support (line 1076+)

# Legacy aliases for compatibility (if needed temporarily)
def get_transactions():
    return get_holdings()

def get_current_holdings():
    return get_holdings()


def add_transaction(ticker_or_data, trade_type=None, qty=None, price=None, trade_date=None, memo=''):
    # [FIX] Support both Dictionary (from API) and Individual Args
    if isinstance(ticker_or_data, dict):
        data = ticker_or_data
        ticker = data['ticker']
        trade_type = data['trade_type']
        qty = int(data.get('qty', 0))
        price = float(data.get('price', 0))
        memo = data.get('memo', '')
        trade_date = data.get('trade_date')
        # [Ver 6.2] New fields
        category = data.get('category', '기타')
        group_name = data.get('group_name', '')
        # [Ver 6.3] is_holding (Boolean)
        is_holding = data.get('is_holding', True)
        if isinstance(is_holding, str):
             is_holding = (is_holding.upper() == 'Y' or is_holding.lower() == 'true')
        
        expected_sell_date = data.get('expected_sell_date')
        target_sell_price = data.get('target_sell_price')
        strategy_memo = data.get('strategy_memo', '')
    else:
        ticker = ticker_or_data
        qty = int(qty) if qty else 0
        price = float(price) if price else 0
        category = '기타'
        group_name = ''
        is_holding = True
        expected_sell_date = None
        target_sell_price = None
        strategy_memo = ''

    # 1. Insert into journal_transactions (Source of Truth for Analysis)
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO journal_transactions 
            (ticker, trade_type, qty, price, trade_date, memo, category, group_name, expected_sell_date, target_sell_price, strategy_memo)
            VALUES (%s, %s, %s, %s, COALESCE(%s, NOW()), %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (ticker, trade_type, qty, price, trade_date, memo, category, group_name, expected_sell_date, target_sell_price, strategy_memo))
            conn.commit()
    except Exception as e:
        print(f"Insert Transaction Error: {e}")
    finally:
        conn.close()

    # 2. Update Managed Stocks (Snapshot for Frontend)
    if trade_type == 'RESET':
        return update_holding(ticker, qty, price, memo, is_reset=True, category=category, group_name=group_name, is_holding=is_holding, expected_sell_date=expected_sell_date, target_sell_price=target_sell_price, strategy_memo=strategy_memo)
    else:
        qty_change = qty if trade_type == 'BUY' else -qty
        return update_holding(ticker, qty_change, price, memo, is_reset=False, category=category, group_name=group_name, is_holding=is_holding, expected_sell_date=expected_sell_date, target_sell_price=target_sell_price, strategy_memo=strategy_memo)

def update_transaction(id, data):
    # Backward compatibility: For now, we just update journal_transactions log.
    # Recalculating holdings from history is complex.
    # Recommendation: User should use RESET to correct holdings.
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            UPDATE journal_transactions 
            SET ticker=%s, trade_type=%s, qty=%s, price=%s, trade_date=%s, memo=%s, group_name=%s
            WHERE id=%s
            """
            cursor.execute(sql, (
                data['ticker'],
                data['trade_type'],
                data['qty'],
                data['price'],
                data['trade_date'],
                data.get('memo', ''),
                data.get('group_name', ''),
                id
            ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Update Transaction Error: {e}")
        return False
    finally:
        conn.close()

def delete_transaction(id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM journal_transactions WHERE id=%s", (id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Delete Transaction Error: {e}")
        return False
    finally:
        conn.close()

def update_holding(ticker, qty_change_or_new_qty, price, memo=None, is_reset=False, category=None, group_name=None, is_holding=True, expected_sell_date=None, target_sell_price=None, strategy_memo=None):
    """보유량 및 평단가 업데이트 (매수/매도/RESET)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 기존 보유량 조회
            cursor.execute("SELECT quantity, avg_price FROM managed_stocks WHERE ticker=%s", (ticker,))
            row = cursor.fetchone()
            
            if not row:
                # 종목이 없으면 먼저 생성 (add_stock 호출 권장하지만 여기서도 처리 가능)
                return False, "Managed stock not found. Add stock first."
            
            if is_reset:
                # RESET: Overwrite Quantity and Avg Price
                new_qty = qty_change_or_new_qty
                new_avg = price
            else:
                # Incremental Calculation
                current_qty = row['quantity'] or 0
                current_avg = row['avg_price'] or 0.0
                qty_change = qty_change_or_new_qty
                new_qty = current_qty + qty_change
                
                # 매수(Increase)일 경우 평단가 갱신 (가중평균)
                if qty_change > 0:
                    total_amt = (current_qty * current_avg) + (qty_change * price)
                    new_avg = total_amt / new_qty if new_qty > 0 else 0
                else:
                    # 매도(Decrease)일 경우 평단가 불변 (단, 전량 매도 시 0 처리)
                    new_avg = current_avg if new_qty > 0 else 0

            if new_qty < 0:
                print("Warning: Quantity cannot be negative.")
                # new_qty = 0 # Or allow negative for short? prevent for now.
            
            # [Ver 6.2] Include category fields in update
            cursor.execute("""
                UPDATE managed_stocks 
                SET quantity=%s, avg_price=%s, category=%s, group_name=%s, is_holding=%s, expected_sell_date=%s, target_sell_price=%s, strategy_memo=%s
                WHERE ticker=%s
            """, (new_qty, new_avg, category, group_name, is_holding, expected_sell_date, target_sell_price, strategy_memo, ticker))
            
            conn.commit()
            return True, "Holding updated"
    except Exception as e:
        print(f"Update Holding Error: {e}")
        return False, str(e)
    finally:
        conn.close()

def update_holding_info(ticker, data):
    """
    [Ver 6.5] Direct Update of Managed Stock Info (No Journal Transaction)
    Updates: Qty, AvgPrice, Category, Group, Memo, Strategy, etc.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check if stock exists
            cursor.execute("SELECT ticker FROM managed_stocks WHERE ticker=%s", (ticker,))
            if not cursor.fetchone():
                return False, "Stock not found"

            sql = """
            UPDATE managed_stocks 
            SET quantity=%s, avg_price=%s, category=%s, group_name=%s, 
                is_holding=%s, expected_sell_date=%s, target_sell_price=%s, strategy_memo=%s
            WHERE ticker=%s
            """
            qty = int(data.get('qty', 0))
            price = float(data.get('price', 0))
            category = data.get('category', '기타')
            group_name = data.get('group_name', '')
            
            is_holding = data.get('is_holding', True)
            if isinstance(is_holding, str):
                 is_holding = (is_holding.upper() == 'Y' or is_holding.lower() == 'true')

            # Optional dates
            expected_sell = data.get('expected_sell_date')
            if not expected_sell: expected_sell = None
            
            target_sell = data.get('target_sell_price')
            if not target_sell: target_sell = None

            cursor.execute(sql, (
                qty, price, category, group_name,
                is_holding, expected_sell, target_sell, data.get('strategy_memo', ''),
                ticker
            ))
        conn.commit()
        return True, "Updated successfully"
    except Exception as e:
        print(f"Update Holding Info Error: {e}")
        return False, str(e)
    finally:
        try: conn.close()
        except: pass

def delete_transaction(id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM journal_transactions WHERE id=%s", (id,))
        conn.commit()
        return True
    finally:
        conn.close()

# --- Cheongan 2.0 Helpers ---

def get_managed_stocks():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM managed_stocks ORDER BY group_name, ticker")
            return cursor.fetchall()
    finally:
        conn.close()

def add_managed_stock(data):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO managed_stocks 
            (ticker, name, group_name, buy_strategy, sell_strategy, target_ratio, scenario_yield, memo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                data['ticker'],
                data.get('name', ''),
                data['group_name'],
                data['buy_strategy'],
                data['sell_strategy'],
                data['target_ratio'],
                data.get('scenario_yield', 0),
                data.get('memo', '')
            ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Add Managed Stock Error: {e}")
        return False
    finally:
        conn.close()

def update_managed_stock(id, data):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            UPDATE managed_stocks 
            SET ticker=%s, name=%s, group_name=%s, buy_strategy=%s, sell_strategy=%s, 
                target_ratio=%s, scenario_yield=%s, memo=%s
            WHERE id=%s
            """
            cursor.execute(sql, (
                data['ticker'],
                data.get('name', ''),
                data['group_name'],
                data['buy_strategy'],
                data['sell_strategy'],
                data['target_ratio'],
                data.get('scenario_yield', 0),
                data.get('memo', ''),
                id
            ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Update Managed Stock Error: {e}")
        return False
    finally:
        conn.close()

def update_manual_price(id, price):
    """
    수동으로 현재가 입력
    - is_manual_price를 TRUE로 설정하여 자동 업데이트에서 제외
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            UPDATE managed_stocks 
            SET current_price = %s,
                is_manual_price = TRUE,
                price_updated_at = NOW(),
                is_market_open = TRUE
            WHERE id = %s
            """
            cursor.execute(sql, (price, id))
        conn.commit()
        print(f"✅ 수동 현재가 입력 완료: ID={id}, Price=${price}")
        return True
    except Exception as e:
        print(f"❌ 수동 현재가 입력 오류: {e}")
        return False
    finally:
        conn.close()

def delete_managed_stock(id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM managed_stocks WHERE id=%s", (id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Delete Managed Stock Error: {e}")
        return False
    finally:
        conn.close()

def get_total_capital():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT value_json FROM global_config WHERE key_name='total_capital'")
            row = cursor.fetchone()
            if row and row['value_json']:
                import json
                return float(json.loads(row['value_json']))
            return 10000.0 # Default
    except Exception as e:
        print(f"Error getting capital: {e}")
        return 10000.0
    finally:
        conn.close()

def set_total_capital(amount):
    conn = get_connection()
    try:
        import json
        with conn.cursor() as cursor:
            val = json.dumps(amount)
            # Upsert
            sql = "INSERT INTO global_config (key_name, value_json) VALUES ('total_capital', %s) ON DUPLICATE KEY UPDATE value_json=%s"
            cursor.execute(sql, (val, val))
        conn.commit()
        return True
    finally:
        conn.close()

def update_market_status(regime, details):
    conn = get_connection()
    try:
        import json
        date_str = datetime.now().strftime("%Y-%m-%d")
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO market_status (date, regime, details)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE regime=VALUES(regime), details=VALUES(details)
            """
            cursor.execute(sql, (date_str, regime, json.dumps(details)))
        conn.commit()
    finally:
        conn.close()

def get_latest_market_status():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM market_status ORDER BY date DESC LIMIT 1")
            row = cursor.fetchone()
            if row and isinstance(row['details'], str):
                import json
                row['details'] = json.loads(row['details'])
            return row
    finally:
        conn.close()




def get_ticker_settings():
    """Returns a dict of ticker settings {ticker: is_visible}"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT ticker, is_visible FROM ticker_settings")
            rows = cursor.fetchall()
            return {row['ticker']: bool(row['is_visible']) for row in rows}
    except Exception as e:
        print(f"Error fetching ticker settings: {e}")
        return {}
    finally:
        conn.close()

def update_ticker_setting(ticker, is_visible):
    """Updates visibility for a ticker. Inserts if not exists."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO ticker_settings (ticker, is_visible)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE is_visible = VALUES(is_visible)
            """
            cursor.execute(sql, (ticker, is_visible))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating ticker setting: {e}")
        return False
    finally:
        conn.close()

def get_global_config(key_name, default=None):
    """Retrieve JSON config from global_config table"""
    conn = get_connection()
    try:
        import json
        with conn.cursor() as cursor:
            cursor.execute("SELECT value_json FROM global_config WHERE key_name = %s", (key_name,))
            row = cursor.fetchone()
            if row:
                val = row['value_json']
                return json.loads(val) if isinstance(val, str) else val
            return default
    except Exception as e:
        print(f"Error fetching global config {key_name}: {e}")
        return default
    finally:
        conn.close()

def set_global_config(key_name, value):
    """Save JSON config to global_config table"""
    conn = get_connection()
    try:
        import json
        val = json.dumps(value)
        with conn.cursor() as cursor:
            sql = "INSERT INTO global_config (key_name, value_json) VALUES (%s, %s) ON DUPLICATE KEY UPDATE value_json = VALUES(value_json)"
            cursor.execute(sql, (key_name, val))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving global config {key_name}: {e}")
        return False
    finally:
        conn.close()
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

def save_candle_data(ticker, timeframe, candles_df):
    """
    Save candle dataframe to DB
    candles_df: pandas DataFrame with DatetimeIndex and columns [Open, High, Low, Close, Volume]
    timeframe: '5m' or '30m'
    """
    if candles_df is None or candles_df.empty:
        return
    
    # [DEPRECATED] No longer saving raw candle data to DB (Ver 5.1.0+)
    # Gap Filling + Memory Analysis is now used.
    return

def get_candle_data(ticker, timeframe, limit=100):
    """
    Retrieve cached candle data from DB
    Returns pandas DataFrame with DatetimeIndex
    """
    # [DEPRECATED] Ver 5.1.0
    return None


# [Ver 5.9.2] Enhanced Mini Chart Data with MA and Cross Detection
def get_mini_chart_data(ticker, limit=50):
    """
    5분봉/30분봉 데이터 + MA10/MA30 + 골든/데드크로스 감지
    Returns: {
        'candles_5m': [...],  # 5분봉 데이터
        'candles_30m': [...], # 30분봉 데이터
    }
    """
    table_name = f"{ticker.lower()}_candle_data"
    conn = get_connection()
    try:
        result = {'candles_5m': [], 'candles_30m': []}
        
        with conn.cursor() as cursor:
            # 5분봉 데이터 (MA 계산용 충분한 데이터)
            sql_5m = f"""
                SELECT candle_date, hour, minute, close_price 
                FROM {table_name} 
                WHERE is_30m IS NULL OR is_30m != 'Y'
                ORDER BY candle_date DESC, hour DESC, minute DESC 
                LIMIT %s
            """
            cursor.execute(sql_5m, (limit + 30,))  # MA30용 추가 데이터
            rows_5m = list(reversed(cursor.fetchall()))
            
            # 30분봉 데이터
            sql_30m = f"""
                SELECT candle_date, hour, minute, close_price 
                FROM {table_name} 
                WHERE is_30m = 'Y'
                ORDER BY candle_date DESC, hour DESC, minute DESC 
                LIMIT %s
            """
            cursor.execute(sql_30m, (limit + 30,))
            rows_30m = list(reversed(cursor.fetchall()))
        
        # MA 계산 함수
        def calc_ma(data, period, idx):
            if idx < period - 1:
                return None
            vals = [float(data[i]['close_price']) for i in range(idx - period + 1, idx + 1)]
            return sum(vals) / period
        
        # 5분봉 처리
        prev_cross_5m = None
        for i, r in enumerate(rows_5m):
            if i < 29:  # MA30 계산 불가
                continue
            
            price = float(r['close_price']) if r['close_price'] else 0
            ma10 = calc_ma(rows_5m, 10, i)
            ma30 = calc_ma(rows_5m, 30, i)
            
            # 크로스 감지
            cross = None
            if ma10 and ma30:
                current_cross = 'golden' if ma10 > ma30 else 'dead'
                if prev_cross_5m and current_cross != prev_cross_5m:
                    cross = current_cross
                prev_cross_5m = current_cross
            
            result['candles_5m'].append({
                'time': f"{r['hour']:02d}:{r['minute']:02d}",
                'price': price,
                'ma10': round(ma10, 4) if ma10 else None,
                'ma30': round(ma30, 4) if ma30 else None,
                'cross': cross
            })
        
        # 30분봉 처리
        prev_cross_30m = None
        for i, r in enumerate(rows_30m):
            if i < 29:
                continue
            
            price = float(r['close_price']) if r['close_price'] else 0
            ma10 = calc_ma(rows_30m, 10, i)
            ma30 = calc_ma(rows_30m, 30, i)
            
            cross = None
            if ma10 and ma30:
                current_cross = 'golden' if ma10 > ma30 else 'dead'
                if prev_cross_30m and current_cross != prev_cross_30m:
                    cross = current_cross
                prev_cross_30m = current_cross
            
            result['candles_30m'].append({
                'time': f"{r['hour']:02d}:{r['minute']:02d}",
                'price': price,
                'ma10': round(ma10, 4) if ma10 else None,
                'ma30': round(ma30, 4) if ma30 else None,
                'cross': cross
            })
        
        # 마지막 N개만 반환
        result['candles_5m'] = result['candles_5m'][-limit:]
        result['candles_30m'] = result['candles_30m'][-limit:]
        
        return result
    except Exception as e:
        print(f"Get Mini Chart Data Error: {e}")
        import traceback
        traceback.print_exc()
        return {'candles_5m': [], 'candles_30m': []}
    finally:
        conn.close()

# --- New DB-Centric Data Management (market_candles) ---

def get_last_candle_time(ticker, timeframe):
    """Get the latest candle_time stored in DB for incremental update"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                sql = "SELECT MAX(candle_time) as last_time FROM market_candles WHERE ticker=%s AND timeframe=%s"
                cursor.execute(sql, (ticker, timeframe))
                row = cursor.fetchone()
                return row['last_time'] if row and row['last_time'] else None
    except Exception as e:
        # print(f"Error getting last candle time: {e}")
        return None

def save_market_candles(ticker, timeframe, df, source='yfinance'):
    """Save DataFrame to market_candles table (Upsert)"""
    import pandas as pd
    import pandas as pd
    if df is None or df.empty: return False
    
    # [DEPRECATED] Ver 5.1.0
    return True

def load_market_candles(ticker, timeframe, limit=300):
    """Load candles from DB as DataFrame"""
    # [DEPRECATED] Ver 5.1.0
    return None

def cleanup_old_candles(ticker, days=30):
    """Delete candles older than N days (Default 30)"""
    # [DEPRECATED] Ver 5.1.0
    return True

# --- System Auto-Trading Log (Simulation) ---
def init_system_trade_table():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            CREATE TABLE IF NOT EXISTS system_trades (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10) NOT NULL,
                trade_type VARCHAR(10) NOT NULL, -- BUY or SELL
                price DECIMAL(10, 4) NOT NULL,
                qty DECIMAL(10, 4) DEFAULT 1,
                trade_time DATETIME NOT NULL,
                profit_pct DECIMAL(6, 2) DEFAULT NULL, -- Only for SELL
                realized_pl DECIMAL(10, 2) DEFAULT NULL, -- Only for SELL
                strategy_note VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql)
        conn.commit()
    finally:
        conn.close()

def log_system_trade(trade_data):
    """
    Log a system trade (Buy/Sell)
    trade_data: {ticker, trade_type, price, trade_time, strategy_note}
    Atomic transaction to ensure Buy/Sell sequence? 
    Logic handled in app layer, this just inserts.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # If SELL, calculate profit based on last BUY
            profit_pct = None
            realized_pl = None
            
            if trade_data['trade_type'] == 'SELL':
                # Find last OPEN BUY
                # Simple logic: Find last transaction. If BUY, calculate.
                cursor.execute("SELECT price FROM system_trades WHERE ticker=%s AND trade_type='BUY' ORDER BY trade_time DESC LIMIT 1", (trade_data['ticker'],))
                last_buy = cursor.fetchone()
                if last_buy:
                    buy_price = float(last_buy['price'])
                    sell_price = float(trade_data['price'])
                    profit_pct = ((sell_price - buy_price) / buy_price) * 100
                    realized_pl = sell_price - buy_price # Per unit
            
            sql = """
            INSERT INTO system_trades (ticker, trade_type, price, trade_time, profit_pct, realized_pl, strategy_note)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                trade_data['ticker'],
                trade_data['trade_type'],
                trade_data['price'],
                trade_data['trade_time'],
                profit_pct,
                realized_pl,
                trade_data.get('strategy_note', '')
            ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Log System Trade Error: {e}")
        return False
    finally:
        conn.close()

def get_system_trade_history(limit=50):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM system_trades ORDER BY trade_time DESC LIMIT %s"
            cursor.execute(sql, (limit,))
            return cursor.fetchall()
    finally:
        conn.close()

def get_last_system_trade(ticker):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM system_trades WHERE ticker=%s ORDER BY trade_time DESC LIMIT 1"
            cursor.execute(sql, (ticker,))
            return cursor.fetchone()
    finally:
        conn.close()

def get_system_performance_summary():
    """Calculate Win Rate and Total Return from system_trades"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Win Rate
            sql_win = """
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN profit_pct > 0 THEN 1 ELSE 0 END) as wins
            FROM system_trades 
            WHERE trade_type = 'SELL'
            """
            cursor.execute(sql_win)
            win_stats = cursor.fetchone()
            
            # Avg Return & Total
            sql_ret = "SELECT AVG(profit_pct) as avg_return, SUM(profit_pct) as total_return FROM system_trades WHERE trade_type = 'SELL'"
            cursor.execute(sql_ret)
            ret_stats = cursor.fetchone()
            
            return {
                "total_trades": win_stats['total_trades'],
                "wins": win_stats['wins'],
                "win_rate": (win_stats['wins'] / win_stats['total_trades'] * 100) if win_stats['total_trades'] > 0 else 0,
                "avg_return": ret_stats['avg_return'] or 0,
                "total_return": ret_stats['total_return'] or 0
            }
    finally:
        conn.close()


def update_stock_prices():
    """
    종목관리에 등록된 모든 종목의 현재가를 업데이트
    - KIS API 사용하여 실시간 가격 조회
    - 수동 입력값(is_manual_price=TRUE)은 업데이트 제외
    - 휴장일 감지 및 is_market_open 플래그 설정
    """
    from datetime import datetime
    from kis_api_v2 import get_current_price, get_exchange_code
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # 자동 업데이트 대상 종목 조회 (수동 입력 제외)
                sql = """
                    SELECT ticker, name, exchange, is_manual_price
                    FROM managed_stocks 
                    WHERE is_active = TRUE
                """
                cursor.execute(sql)
                rows = cursor.fetchall()
                
                if not rows:
                    print("⚠️ 등록된 종목이 없습니다")
                    return False
                
                print(f"📊 {len(rows)}개 종목 현재가 업데이트 시작 (KIS -> YF Fallback)...")
                
                updated_count = 0
                skipped_count = 0
                failed_count = 0
                
                import yfinance as yf # Lazy import
                
                for row in rows:
                    ticker = row['ticker']
                    name = row['name']
                    exchange = row.get('exchange')
                    is_manual = row.get('is_manual_price', False)
                    
                    # 수동 입력값은 보호
                    if is_manual:
                        print(f"  ⏭️ {ticker} - 수동 입력값 유지")
                        skipped_count += 1
                        continue
                    
                    try:
                        # 거래소 코드 자동 감지
                        if not exchange:
                            exchange = get_exchange_code(ticker)
                        
                        current_price = 0
                        is_market_open = False
                        source = "None"

                        change_pct = 0.0

                        # 1. KIS API로 현재가 조회
                        # print(f"  🔍 {ticker} ({exchange}) 조회 중... (KIS)")
                        price_data = get_current_price(ticker, exchange)
                        
                        if price_data and price_data.get('price', 0) > 0:
                            current_price = price_data['price']
                            is_market_open = price_data.get('is_open', True)
                            change_pct = price_data.get('rate', 0.0) # KIS returns 'rate'
                            source = "KIS"
                        else:
                            # 2. Skip fallback for SOXS/SOXL? No, user wants ALL.
                            # Fallback to YFinance (Extended Hours)
                            # print(f"  ⚠️ KIS Failed for {ticker}. Trying YF...")
                            try:
                                t = yf.Ticker(ticker)
                                # Get fast info first
                                fast_info = t.fast_info
                                last_price = fast_info.last_price
                                
                                # Check Pre/Post market if available
                                # yfinance often needs history(period="1d", interval="1m", prepost=True) to see latest
                                df = t.history(period="1d", interval="1m", prepost=True)
                                if not df.empty:
                                    last_price = float(df['Close'].iloc[-1])
                                    source = "YF(Ext)"
                                    # Try to calc change pct if possible or use 0
                                else:
                                    source = "YF(Fast)" # Fallback to last close
                                    
                                if last_price and last_price > 0:
                                    current_price = last_price
                            except Exception as e:
                                # print(f"  ❌ YF Failed: {e}")
                                pass
                        
                        if current_price and current_price > 0:
                            # 현재가 업데이트 (managed_stocks)
                            update_sql = """
                                UPDATE managed_stocks 
                                SET current_price = %s, 
                                    price_updated_at = NOW(),
                                    is_market_open = %s
                                WHERE ticker = %s
                            """
                            cursor.execute(update_sql, (current_price, is_market_open, ticker))
                            
                            # [Ver 5.7] Sync removed as per user request (Keep market_indices clean)
                            # sync_sql = ...
                            
                            conn.commit() # Commit per row to ensure partial success
                            updated_count += 1
                            print(f"  ✅ {ticker}: ${current_price:,.2f} ({source})")
                        else:
                            print(f"  ❌ {ticker}: 가격 조회 실패")
                            failed_count += 1

                    except Exception as e:
                        print(f"  ❌ {ticker} 업데이트 오류: {e}")
                        failed_count += 1
                        continue
                
                conn.commit()
                print(f"\n✅ 업데이트 완료: {updated_count}개 성공, {skipped_count}개 스킵(수동), {failed_count}개 실패")
                return True
                
    except Exception as e:
        print(f"❌ 현재가 업데이트 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_stock_current_price(ticker):
    """특정 종목의 현재가 조회 (캐시된 값)"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                    SELECT current_price, price_updated_at, is_market_open 
                    FROM managed_stocks 
                    WHERE ticker = %s AND is_active = TRUE
                """
                cursor.execute(sql, (ticker,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'price': row[0],
                        'updated_at': row[1],
                        'is_market_open': row[2]
                    }
                return None
    except Exception as e:
        print(f"현재가 조회 오류 ({ticker}): {e}")
        return None

# --- User Management ---
def create_user(email, password_hash, name):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                sql = "INSERT INTO users (email, password_hash, name) VALUES (%s, %s, %s)"
                cursor.execute(sql, (email, password_hash, name))
                conn.commit()
                return True
    except Exception as e:
        print(f"Error creating user: {e}")
        return False

def get_user_by_email(email):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM users WHERE email = %s"
                cursor.execute(sql, (email,))
                return cursor.fetchone()
    except Exception as e:
        print(f"Error getting user by email: {e}")
        return None

def create_trade(ticker, price, entry_time):
    """Start a new trade"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO trade_history (ticker, entry_time, entry_price, status, strategy_ver)
                VALUES (%s, %s, %s, 'OPEN', '5.7')
            """
            cursor.execute(sql, (ticker, entry_time, price))
        conn.commit()
    finally:
        conn.close()

def close_trade(ticker, exit_price, exit_time):
    """Close an open trade"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Get Open Trade
            cursor.execute("SELECT id, entry_price FROM trade_history WHERE ticker=%s AND status='OPEN' LIMIT 1", (ticker,))
            trade = cursor.fetchone()
            if trade:
                entry_price = float(trade['entry_price'])
                try:
                    profit = ((float(exit_price) - entry_price) / entry_price) * 100
                except: profit = 0
                
                sql = """
                    UPDATE trade_history 
                    SET exit_time=%s, exit_price=%s, profit_pct=%s, status='CLOSED'
                    WHERE id=%s
                """
                cursor.execute(sql, (exit_time, exit_price, profit, trade['id']))
                conn.commit()
                return True
    finally:
        conn.close()
    return False

def check_open_trade(ticker):
    """Check if there is an active trade for ticker"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM trade_history WHERE ticker=%s AND status='OPEN' LIMIT 1"
            cursor.execute(sql, (ticker,))
            return cursor.fetchone()
    finally:
        conn.close()

def get_managed_stock_price(ticker):
    """
    Get current price and change from managed_stocks table.
    Returns: {'price': float, 'change': float} or None
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT current_price FROM managed_stocks WHERE ticker=%s"
            cursor.execute(sql, (ticker,))
            row = cursor.fetchone()
            if row:
                return {
                    'price': float(row['current_price']) if row['current_price'] else 0.0,
                    'change': 0.0
                }
            return None
    except Exception as e:
        print(f"Error getting managed stock price ({ticker}): {e}")
        return None
    finally:
        conn.close()

def get_trade_history(limit=50):
    """Get recent trades for UI"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Recent first
            sql = "SELECT * FROM trade_history ORDER BY entry_time DESC LIMIT %s"
            cursor.execute(sql, (limit,))
            return cursor.fetchall()
    finally:
        conn.close()

# --- Cheongan V2 Helper Functions ---

def log_history(manage_id, ticker, event_type, msg=None, price=None):
    """이벤트/신호 이력을 history 테이블에 저장 (30분 내 중복 방지)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 30분 이내 동일한 이벤트(ticker, event_type, msg)가 있는지 확인
            check_sql = """
                SELECT event_dt FROM history 
                WHERE ticker=%s AND event_type=%s AND short_msg=%s 
                AND event_dt > NOW() - INTERVAL '30 minutes'
                LIMIT 1
            """
            cursor.execute(check_sql, (ticker, event_type, msg))
            if cursor.fetchone():
                return True # 중복 기록 방지 (성공으로 처리)

            sql = """
                INSERT INTO history (manage_id, ticker, event_type, short_msg, event_price, event_dt) 
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(sql, (manage_id, ticker, event_type, msg, price))
        conn.commit()
        return True
    except Exception as e:
        print(f"Log History Error: {e}")
        return False
    finally:
        conn.close()

def get_v2_buy_status(ticker):
    """현재 진행 중인 매수 신호 상태 조회 (최신 1건)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT * FROM buy_stock 
                WHERE ticker = %s 
                ORDER BY row_dt DESC LIMIT 1
            """
            cursor.execute(sql, (ticker,))
            return cursor.fetchone()
    finally:
        conn.close()

def create_initial_buy_record(ticker, manage_id):
    """[Ver 5.8.3] 신호 추적용 초기 매수 레코드 생성"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 기존 레코드 확인
            cursor.execute("SELECT 1 FROM buy_stock WHERE ticker=%s", (ticker,))
            if cursor.fetchone():
                return True  # 이미 존재
            
            sql = """
                INSERT INTO buy_stock (ticker, manage_id, row_dt)
                VALUES (%s, %s, NOW())
            """
            cursor.execute(sql, (ticker, manage_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Create Initial Buy Record Error: {e}")
        return False
    finally:
        conn.close()



def get_v2_sell_status(ticker):
    """현재 보유 중인 종목의 청산 상태 조회"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT * FROM sell_stock 
                WHERE ticker = %s AND close_yn = 'N'
                ORDER BY row_dt DESC LIMIT 1
            """
            cursor.execute(sql, (ticker,))
            return cursor.fetchone()
    finally:
        conn.close()

def create_v2_sell_record(ticker, entry_price):
    """최종 진입 확정 시 sell_stock 레코드 생성"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check if exists first
            cursor.execute("SELECT 1 FROM sell_stock WHERE ticker=%s", (ticker,))
            if cursor.fetchone():
                return True # Already exists

            sql = """
                INSERT INTO sell_stock (ticker, final_sell_price, row_dt)
                VALUES (%s, 0, NOW())
            """
            cursor.execute(sql, (ticker,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Create Sell Record Error: {e}")
        return False
    finally:
        conn.close()

def save_v2_buy_signal(ticker, signal_type, price, status='Y'):
    """매수 신호 단계별 업데이트 (Auto Logic) - Uses Ticker Only"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Check Manual Flag & Existence
            # Add ticker column to SELECT to ensure we are looking at the right record logic if needed, but ticker is passed.
            cols = "is_manual_buy1, is_manual_buy2, is_manual_buy3"
            cursor.execute(f"SELECT {cols} FROM buy_stock WHERE ticker=%s", (ticker,))
            row = cursor.fetchone()
            
            # Logic: If row doesn't exist, we must create it IF signal is 'sig1' and status is 'Y'.
            # If row exists, we check manual flags.
            
            if not row:
                if signal_type == 'sig1' and status == 'Y':
                    # Create New Record
                    sql_insert = """
                        INSERT INTO buy_stock (ticker, row_dt, buy_sig1_yn, buy_sig1_price, buy_sig1_dt)
                        VALUES (%s, NOW(), 'Y', %s, NOW())
                    """
                    cursor.execute(sql_insert, (ticker, price))
                    conn.commit()
                    return True
                else:
                    return False # Cannot update non-existent record for later signals or if status is N
            
            # Row exists, check flags
            # Row exists, check flags
            is_man_1, is_man_2, is_man_3 = row
            print(f"DEBUG_PROTECT: Ticker={ticker}, Man1={is_man_1}, Man2={is_man_2}, Man3={is_man_3}")
            
            sql = ""
            if signal_type == 'sig1':
                if str(is_man_1) == 'Y': 
                    print(f"DEBUG_PROTECT: Skipping Sig1 Update for {ticker} (Manual)")
                    return True # Manual Override (Skip Auto)
                sql = "UPDATE buy_stock SET buy_sig1_yn=%s, buy_sig1_price=%s, buy_sig1_dt=NOW() WHERE ticker=%s"
            elif signal_type == 'sig2':
                if str(is_man_2) == 'Y': return True
                sql = "UPDATE buy_stock SET buy_sig2_yn=%s, buy_sig2_price=%s, buy_sig2_dt=NOW() WHERE ticker=%s"
            elif signal_type == 'sig3':
                if str(is_man_3) == 'Y': return True
                sql = "UPDATE buy_stock SET buy_sig3_yn=%s, buy_sig3_price=%s, buy_sig3_dt=NOW() WHERE ticker=%s"
            elif signal_type == 'final':
                sql = "UPDATE buy_stock SET final_buy_yn=%s, final_buy_price=%s, final_buy_dt=NOW() WHERE ticker=%s"
            
            if sql:
                cursor.execute(sql, (status, price, ticker))
                conn.commit()
                return True
            return False
    except Exception as e:
        print(f"Save Buy Signal Error: {e}")
        return False
    finally:
        conn.close()

def save_v2_sell_signal(ticker, signal_type, price, status='Y'):
    """청산 신호 단계별 업데이트 (Auto Logic) - Uses Ticker Only"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
             # Check Manual Flag First
            cols = "is_manual_sell1, is_manual_sell2, is_manual_sell3"
            cursor.execute(f"SELECT {cols} FROM sell_stock WHERE ticker=%s", (ticker,))
            row = cursor.fetchone()
            
            if not row:
                # If sell record doesn't exist, we usually don't create it here (created by confirm_buy or manually)
                # But if user wants to track sell signals even before full buy confirmation? 
                # Ideally sell_stock exists when we hold stock.
                return False 
                
            is_man_1, is_man_2, is_man_3 = row

            sql = ""
            if signal_type == 'sig1':
                if is_man_1 == 'Y': return True
                sql = "UPDATE sell_stock SET sell_sig1_yn=%s, sell_sig1_price=%s, sell_sig1_dt=NOW() WHERE ticker=%s"
            elif signal_type == 'sig2':
                if is_man_2 == 'Y': return True
                sql = "UPDATE sell_stock SET sell_sig2_yn=%s, sell_sig2_price=%s, sell_sig2_dt=NOW() WHERE ticker=%s"
            elif signal_type == 'sig3':
                if is_man_3 == 'Y': return True
                sql = "UPDATE sell_stock SET sell_sig3_yn=%s, sell_sig3_price=%s, sell_sig3_dt=NOW() WHERE ticker=%s"
            elif signal_type == 'final':
                sql = "UPDATE sell_stock SET final_sell_yn=%s, final_sell_price=%s, final_sell_dt=NOW() WHERE ticker=%s"
            
            if sql:
                cursor.execute(sql, (status, price, ticker))
                conn.commit()
                return True
            return False
    except Exception as e:
        print(f"Save Sell Signal Error: {e}")
        return False
    finally:
        conn.close()



def fetch_signal_status_dict(ticker):
    """
    Fetch comprehensive signal status for analysis logic (returns dict keys).
    Returns {'buy': dict, 'sell': dict}
    """
    conn = get_connection()
    try:
        import pymysql.cursors
        # Use DictCursor explicitly
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 1. Buy Status
            cursor.execute("SELECT * FROM buy_stock WHERE ticker=%s ORDER BY row_dt DESC LIMIT 1", (ticker,))
            buy_row = cursor.fetchone()
            
            # 2. Sell Status
            cursor.execute("SELECT * FROM sell_stock WHERE ticker=%s ORDER BY row_dt DESC LIMIT 1", (ticker,))
            sell_row = cursor.fetchone()
            
            return {'buy': buy_row, 'sell': sell_row}
    except Exception as e:
        print(f"Fetch Signal Status Error: {e}")
        return {'buy': None, 'sell': None}
    finally:
        conn.close()


def update_v2_target_price(ticker, target_type, price):
    """Set custom target price for Box(Buy2) or Stop(Sell2)"""
    # target_type: 'box' or 'stop'
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            if target_type == 'box':
                sql = "UPDATE buy_stock SET target_box_price=%s WHERE ticker=%s"
            elif target_type == 'stop':
                sql = "UPDATE sell_stock SET target_stop_price=%s WHERE ticker=%s"
            else:
                return False
            
            cursor.execute(sql, (price, ticker))
            conn.commit()
            return True
    except Exception as e:
        print(f"Update Target Error: {e}")
        return False
    finally:
        conn.close()

def confirm_v2_buy(ticker, price, qty):
    """사용자 실제 매수 확정 입력"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Update buy_stock with real info
            sql = """
                UPDATE buy_stock
                SET real_buy_yn = 'Y', 
                    real_buy_price = %s, 
                    real_buy_qn = %s,
                    real_buy_dt = NOW(),
                    /* [Ver 5.3 Force Entry] Force all signals to Y if manually confirmed */
                    final_buy_yn = 'Y',
                    buy_sig1_yn = 'Y',
                    buy_sig2_yn = 'Y',
                    buy_sig3_yn = 'Y',
                    is_manual_buy1 = 'Y',
                    is_manual_buy2 = 'Y',
                    is_manual_buy3 = 'Y'
                WHERE ticker = %s
            """
            cursor.execute(sql, (price, qty, ticker))
            
            # Optional: Create sell_stock entry if doesn't exist
            sql2 = """
                INSERT INTO sell_stock (ticker, row_dt)
                VALUES (%s, NOW())
                ON DUPLICATE KEY UPDATE row_dt=NOW()
            """
            cursor.execute(sql2, (ticker,))

            
        conn.commit()
        return True, "Buy Confirmed"
    except Exception as e:
        print(f"Confirm Buy Error: {e}")
        return False, str(e)
    finally:
        conn.close()

def confirm_v2_sell(ticker, price, qty, is_end=False):
    """사용자 실제 매도(청산) 확정 입력"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            if is_end:
                # [Ver 5.0] 종결/청산 시 히스토리(system_trades) 저장
                cursor.execute("SELECT real_buy_price, real_buy_qn FROM buy_stock WHERE ticker = %s", (ticker,))
                buy_row = cursor.fetchone()
                
                if buy_row:
                    buy_price = float(buy_row['real_buy_price'] or 0)
                    # Use provided qty or fallback to stored buy qty
                    close_qty = float(qty) if qty and float(qty) > 0 else float(buy_row['real_buy_qn'] or 0)
                    
                    if buy_price > 0:
                        profit_pct = ((price - buy_price) / buy_price) * 100
                        profit_amt = (price - buy_price) * close_qty
                        
                        # Save History
                        hist_sql = """
                            INSERT INTO system_trades
                            (ticker, trade_type, price, qty, trade_time, profit_pct, realized_pl, strategy_note)
                            VALUES (%s, 'SELL', %s, %s, NOW(), %s, %s, 'Ver5.0 종결')
                        """
                        cursor.execute(hist_sql, (ticker, price, close_qty, profit_pct, profit_amt))
                        print(f"📜 [History] {ticker} Close: {profit_pct:.2f}% (${profit_amt:.2f}) Saved.")

                # 종결/청산: 레코드 삭제
                cursor.execute("DELETE FROM sell_stock WHERE ticker = %s", (ticker,))
                cursor.execute("DELETE FROM buy_stock WHERE ticker = %s", (ticker,))
                print(f"[종결/청산] {ticker} 레코드 삭제 완료 - 새 사이클 대기")
            else:
                # 부분 매도 정보 업데이트 (종결 아닌 경우)
                sql = """
                    UPDATE sell_stock
                    SET real_sell_avg_price = %s,
                        real_sell_qn = %s,
                        real_sell_dt = NOW()
                    WHERE ticker = %s
                """
                cursor.execute(sql, (price, qty, ticker))
                if cursor.rowcount == 0:
                    return False, "참조하는 매매 데이터(Ticker)를 찾을 수 없습니다."

        conn.commit()
        return True, "Success"
    except Exception as e:
        print(f"Confirm V2 Sell Error: {e}")
        return False, str(e)
    finally:
        conn.close()


def manual_update_signal(ticker, signal_key, price, status='Y'):
    """
    수동으로 신호 상태 변경 (1차, 2차, 3차)
    signal_key: 'buy1', 'buy2', 'buy3', 'sell1', 'sell2', 'sell3'
    status: 'Y' (Set) or 'N' (Cancel)
    ticker: SOXL, SOXS, etc.
    """
    conn = get_connection()
    try:
        # Map key to columns (Added is_manual column)
        mapping = {
            'buy1': ('buy_stock', 'buy_sig1_yn', 'buy_sig1_price', 'buy_sig1_dt', 'is_manual_buy1'),
            'buy2': ('buy_stock', 'buy_sig2_yn', 'buy_sig2_price', 'buy_sig2_dt', 'is_manual_buy2'),
            'buy3': ('buy_stock', 'buy_sig3_yn', 'buy_sig3_price', 'buy_sig3_dt', 'is_manual_buy3'),
            'sell1': ('sell_stock', 'sell_sig1_yn', 'sell_sig1_price', 'sell_sig1_dt', 'is_manual_sell1'),
            'sell2': ('sell_stock', 'sell_sig2_yn', 'sell_sig2_price', 'sell_sig2_dt', 'is_manual_sell2'),
            'sell3': ('sell_stock', 'sell_sig3_yn', 'sell_sig3_price', 'sell_sig3_dt', 'is_manual_sell3')
        }
        
        if signal_key not in mapping:
            return False
            
        table, col_yn, col_price, col_dt, col_manual = mapping[signal_key]
        
        print(f"DEBUG_MANUAL: Key={signal_key}, Table={table}, Status={status}, Ticker={ticker}")

        if status == 'SET_TARGET' and signal_key.startswith('sell'):
            step_idx = int(signal_key[-1])
            target_col = f"manual_target_sell{step_idx}"
            
            conn = get_connection()
            try:
                with conn.cursor() as cursor:
                     # Check existence
                     cursor.execute(f"SELECT 1 FROM {table} WHERE ticker=%s", (ticker,))
                     if not cursor.fetchone():
                         init_sql = f"INSERT INTO {table} (ticker, row_dt) VALUES (%s, NOW())"
                         cursor.execute(init_sql, (ticker,))
                     
                     print(f"Updating Target: {target_col} = {price} for {ticker}")
                     sql = f"UPDATE {table} SET {target_col}=%s WHERE ticker=%s"
                     cursor.execute(sql, (price, ticker))
                     conn.commit()
                return True
            finally:
                conn.close()

        
        # Determine Manual Flag: 'Y' if setting signal (status='Y'), 'N' if cancelling (status='N')
        # User wants: Manual Set -> Fixed ON (is_manual='Y')
        #             Manual Cancel -> Auto Mode (is_manual='N')
        is_manual_val = 'Y' if status == 'Y' else 'N'

        with conn.cursor() as cursor:
            # Check existence first
            check_sql = f"SELECT 1 FROM {table} WHERE ticker=%s"
            cursor.execute(check_sql, (ticker,))
            exists = cursor.fetchone()
            
            if not exists:
                if table == 'buy_stock' and status == 'Y':
                    # Create New Record for buy_stock
                    sql_insert = f"""
                        INSERT INTO buy_stock (ticker, row_dt, {col_yn}, {col_price}, {col_dt}, {col_manual})
                        VALUES (%s, NOW(), %s, %s, NOW(), %s)
                    """
                    cursor.execute(sql_insert, (ticker, status, price, is_manual_val))
                elif table == 'sell_stock' and status == 'Y':
                    # Create New Record for sell_stock (when in SELL mode)
                    sql_insert = f"""
                        INSERT INTO sell_stock (ticker, row_dt, {col_yn}, {col_price}, {col_dt}, {col_manual})
                        VALUES (%s, NOW(), %s, %s, NOW(), %s)
                    """
                    cursor.execute(sql_insert, (ticker, status, price, is_manual_val))
                else:
                    print(f"Manual Update Skipped: Record not found for {ticker}")
                    return False

            else:
                # Update existing
                sql = f"""
                    UPDATE {table}
                    SET {col_yn} = %s, 
                        {col_price} = %s, 
                        {col_dt} = NOW(),
                        {col_manual} = %s
                    WHERE ticker = %s
                """
                cursor.execute(sql, (status, price, is_manual_val, ticker))

            
            # [FIX] Clear Custom Targets when Resetting Signal (N)
            if status == 'N':
                if signal_key == 'buy2':
                    clear_sql = "UPDATE buy_stock SET target_box_price = NULL WHERE ticker=%s"
                    cursor.execute(clear_sql, (ticker,))
                elif signal_key == 'sell2':
                    # Clear both old target_stop_price and new manual_target_sell2
                    clear_sql = "UPDATE sell_stock SET target_stop_price = NULL, manual_target_sell2 = NULL WHERE ticker=%s"
                    cursor.execute(clear_sql, (ticker,))
                
                # [NEW] Clear Manual Sell Targets for Step 1 & 3
                if signal_key == 'sell1':
                    cursor.execute("UPDATE sell_stock SET manual_target_sell1 = NULL WHERE ticker=%s", (ticker,))
                elif signal_key == 'sell3':
                    cursor.execute("UPDATE sell_stock SET manual_target_sell3 = NULL WHERE ticker=%s", (ticker,))

            # Logic for final_buy only if status is 'Y'
            if status == 'Y' and signal_key == 'buy3':
                 cursor.execute("UPDATE buy_stock SET final_buy_yn='Y', final_buy_price=%s, final_buy_dt=NOW() WHERE ticker=%s", (price, ticker))
            
            
        conn.commit()
        return True
    except Exception as e:
        print(f"Manual Update Error: {e}")
        return False
    finally:
        conn.close()

def delete_v2_record(ticker):
    """Delete both buy and sell records (full cycle reset) by ticker"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM sell_stock WHERE ticker=%s", (ticker,))
            cursor.execute("DELETE FROM buy_stock WHERE ticker=%s", (ticker,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Delete V2 Record Error: {e}")
        return False
    finally:
        conn.close()

def delete_v2_sell_only(ticker):
    """Delete sell record only (reset to buy mode) by ticker"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM sell_stock WHERE ticker=%s", (ticker,))
            # Reset buy final flag to allow new cycle
            cursor.execute("UPDATE buy_stock SET final_buy_yn='N' WHERE ticker=%s", (ticker,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Delete Sell Record Error: {e}")
        return False
    finally:
        conn.close()

def update_market_indices(data_list):
    """
    Update market indices in bulk.
    data_list: list of dicts {'ticker': 'S&P500', 'name': 'S&P 500', 'price': 1234.56, 'change': 1.23}
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO market_indices (ticker, name, current_price, change_pct)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            current_price = VALUES(current_price),
            change_pct = VALUES(change_pct)
            """
            for item in data_list:
                cursor.execute(sql, (item['ticker'], item['name'], item['price'], item['change']))
        conn.commit()
    except Exception as e:
        print(f"Update Indices Error: {e}")
    finally:
        conn.close()

def get_market_indices():
    """Return list of market_indices records"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM market_indices")
            return cursor.fetchall()
    except Exception as e:
        print(f"Get Indices Error: {e}")
        return []
    finally:
        conn.close()

def manual_update_market_indices(ticker, price, change_pct=0.0):
    """수동으로 market_indices 특정 ticker 가격 업데이트"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check if ticker exists
            cursor.execute("SELECT 1 FROM market_indices WHERE ticker = %s", (ticker,))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing
                sql = """
                    UPDATE market_indices 
                    SET current_price = %s, change_pct = %s, updated_at = NOW()
                    WHERE ticker = %s
                """
                cursor.execute(sql, (price, change_pct, ticker))
            else:
                # Insert new
                sql = """
                    INSERT INTO market_indices (ticker, name, current_price, change_pct)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (ticker, ticker, price, change_pct))
                
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Manual Market Indices Update Error: {e}")
        return False
    finally:
        conn.close()

def get_latest_market_indicators(ticker):
    """특정 Ticker의 최신 보조지표 조회 (Snapshot)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT * FROM market_indicators_snapshot 
                WHERE ticker = %s 
            """
            cursor.execute(sql, (ticker,))
            return cursor.fetchone()
    except Exception as e:
        print(f"Get Indicators Error: {e}")
        return None
    finally:
        conn.close()

def manual_update_market_indicators(ticker, rsi, vr, atr, pivot_r1):
    """보조지표 수동 업데이트 (Upsert)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Upsert Logic
            sql = """
                INSERT INTO market_indicators_log 
                (ticker, candle_time, rsi_14, vol_ratio, atr, pivot_r1, created_at)
                VALUES (%s, NOW(), %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                rsi_14 = VALUES(rsi_14),
                vol_ratio = VALUES(vol_ratio),
                atr = VALUES(atr),
                pivot_r1 = VALUES(pivot_r1),
                created_at = NOW(),
                candle_time = NOW()
            """
            cursor.execute(sql, (ticker, rsi, vr, atr, pivot_r1))
        conn.commit()
        return True
    except Exception as e:
        print(f"Manual Indicators Update Error: {e}")
        return False
    finally:
        conn.close()

# ========================================
# Trading Journal (거래일지) CRUD Functions
# ========================================

def get_trade_journals(status=None, ticker=None, limit=100):
    """거래일지 목록 조회 (필터 지원)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM trade_journal WHERE 1=1"
            params = []
            
            if status:
                sql += " AND status = %s"
                params.append(status)
            if ticker:
                sql += " AND ticker = %s"
                params.append(ticker)
            
            sql += " ORDER BY buy_date DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(sql, params)
            return cursor.fetchall()
    except Exception as e:
        print(f"Get Journals Error: {e}")
        return []
    finally:
        conn.close()

def get_trade_journal_by_id(journal_id):
    """단일 거래 조회"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM trade_journal WHERE id = %s", (journal_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"Get Journal Error: {e}")
        return None
    finally:
        conn.close()

def create_trade_journal(data):
    """새 거래 기록 생성"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO trade_journal 
            (ticker, buy_date, buy_price, buy_qty, buy_reason, 
             market_condition, total_assets, prediction_score, score_at_entry, tags, screenshot, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'OPEN')
            """
            cursor.execute(sql, (
                data.get('ticker'),
                data.get('buy_date'),
                data.get('buy_price'),
                data.get('buy_qty', 1),
                data.get('buy_reason'),
                data.get('market_condition'),
                data.get('total_assets'),
                data.get('prediction_score'),
                data.get('score_at_entry'),
                data.get('tags'),
                data.get('screenshot')
            ))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Create Journal Error: {e}")
        return None
    finally:
        conn.close()

def update_trade_journal(journal_id, data):
    """거래 수정 (청산 정보 추가 포함)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Build dynamic update query
            fields = []
            params = []
            
            updatable = ['sell_date', 'sell_price', 'sell_qty', 'sell_reason',
                         'market_condition', 'total_assets', 'prediction_score', 'emotion_after',
                         'score_at_entry', 'score_at_exit', 'realized_pnl',
                         'realized_pnl_pct', 'hold_days', 'lesson', 'tags', 'status',
                         'buy_date', 'buy_price', 'buy_qty', 'buy_reason', 'screenshot']
            
            for field in updatable:
                if field in data and data[field] is not None:
                    fields.append(f"{field} = %s")
                    params.append(data[field])
            
            if not fields:
                return False
            
            params.append(journal_id)
            sql = f"UPDATE trade_journal SET {', '.join(fields)} WHERE id = %s"
            cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Update Journal Error: {e}")
        return False
    finally:
        conn.close()

def delete_trade_journal(journal_id):
    """거래 삭제"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM trade_journal WHERE id = %s", (journal_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Delete Journal Error: {e}")
        return False
    finally:
        conn.close()

def get_trade_journal_stats():
    """거래일지 통계 조회"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            stats = {}
            
            # 총 거래 수
            cursor.execute("SELECT COUNT(*) as total FROM trade_journal")
            stats['total_trades'] = cursor.fetchone()['total']
            
            # OPEN / CLOSED 수
            cursor.execute("SELECT status, COUNT(*) as cnt FROM trade_journal GROUP BY status")
            for row in cursor.fetchall():
                stats[f"{row['status'].lower()}_trades"] = row['cnt']
            
            # 승률 (CLOSED & profit > 0)
            cursor.execute("""
                SELECT 
                    COUNT(*) as closed_total,
                    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) as losses,
                    AVG(realized_pnl_pct) as avg_pnl_pct,
                    SUM(realized_pnl) as total_pnl
                FROM trade_journal WHERE status = 'CLOSED'
            """)
            closed_stats = cursor.fetchone()
            stats['closed_total'] = closed_stats['closed_total'] or 0
            stats['wins'] = closed_stats['wins'] or 0
            stats['losses'] = closed_stats['losses'] or 0
            stats['win_rate'] = round((stats['wins'] / stats['closed_total'] * 100), 1) if stats['closed_total'] > 0 else 0
            stats['avg_pnl_pct'] = round(float(closed_stats['avg_pnl_pct'] or 0), 2)
            stats['total_pnl'] = round(float(closed_stats['total_pnl'] or 0), 2)
            
            # 종목별 통계
            cursor.execute("""
                SELECT ticker, COUNT(*) as cnt, 
                       SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                       AVG(realized_pnl_pct) as avg_pnl
                FROM trade_journal WHERE status = 'CLOSED'
                GROUP BY ticker
            """)
            stats['by_ticker'] = cursor.fetchall()
            
            return stats
    except Exception as e:
        print(f"Get Stats Error: {e}")
        return {}
    finally:
        conn.close()

# ========================================
# Daily Assets & Strategy Functions Import
# ========================================
from db_asset_strategy import (
    get_daily_assets, upsert_daily_asset, delete_daily_asset, get_asset_summary,
    get_asset_goals, create_asset_goal, update_asset_goal, delete_asset_goal,
    get_trading_strategies, get_trading_strategy_by_id, 
    create_trading_strategy, update_trading_strategy, delete_trading_strategy,
    get_strategy_performance
)


# [Ver 5.4] Manual Price Level Alerts
def get_price_levels(ticker):
    """Fetch all manual price levels for a ticker"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM manual_price_levels WHERE ticker=%s ORDER BY level_type, stage"
            cursor.execute(sql, (ticker,))
            return cursor.fetchall()  # List of dicts
    except Exception as e:
        print(f"Get Price Levels Error: {e}")
        return []
    finally:
        conn.close()

def update_price_level(ticker, level_type, stage, price, is_active):
    """Update a specific price level"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO manual_price_levels (ticker, level_type, stage, price, is_active, triggered, updated_at)
                VALUES (%s, %s, %s, %s, %s, 'N', NOW())
                ON DUPLICATE KEY UPDATE
                    price=VALUES(price),
                    is_active=VALUES(is_active),
                    triggered='N',
                    updated_at=NOW()
            """
            cursor.execute(sql, (ticker, level_type, stage, price, is_active))
        conn.commit()
        return True
    except Exception as e:
        print(f"Update Price Level Error: {e}")
        return False
    finally:
        conn.close()

def set_price_level_triggered(ticker, level_type, stage):
    """Mark a level as triggered"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                UPDATE manual_price_levels 
                SET triggered='Y', triggered_at=NOW()
                WHERE ticker=%s AND level_type=%s AND stage=%s
            """
            cursor.execute(sql, (ticker, level_type, stage))
        conn.commit()
    except Exception as e:
        print(f"Set Triggered Error: {e}")
    finally:
        conn.close()

def reset_price_level_trigger(ticker, level_type, stage):
    """Reset trigger status (Re-arm) - 가격도 0으로 리셋"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                UPDATE manual_price_levels 
                SET triggered='N', is_active='N', price=0, updated_at=NOW()
                WHERE ticker=%s AND level_type=%s AND stage=%s
            """
            cursor.execute(sql, (ticker, level_type, stage))
        conn.commit()
        return True
    except Exception as e:
        print(f"Reset Trigger Error: {e}")
        return False
    finally:
        conn.close()

def reset_price_level_triggered_only(ticker, level_type, stage):
    """[Ver 5.8.4] triggered만 N으로 리셋 (가격/활성 상태 유지)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                UPDATE manual_price_levels 
                SET triggered='N'
                WHERE ticker=%s AND level_type=%s AND stage=%s
            """
            cursor.execute(sql, (ticker, level_type, stage))
        conn.commit()
        return True
    except Exception as e:
        print(f"Reset Triggered Only Error: {e}")
        return False
    finally:
        conn.close()

# [Ver 5.5] Manual Target Update Helper
def update_manual_target(ticker, target_type, price):
    """Update manual sell target (e.g. sell2) for a ticker"""
    conn = get_connection()
    try:
        col_name = f"manual_target_{target_type}" # manual_target_sell2
        with conn.cursor() as cursor:
            sql = f"UPDATE sell_stock SET {col_name}=%s, updated_at=NOW() WHERE ticker=%s"
            cursor.execute(sql, (price, ticker))
        conn.commit()
        return True
    except Exception as e:
        print(f"Update Manual Target Error: {e}")
        return False
    finally:
        conn.close()

# [Ver 6.2] Add new columns to journal_transactions for category/strategy
def migrate_journal_transactions_v62():
    """Add category, expected_sell_date, target_sell_price, strategy_memo columns"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check if columns exist
            cursor.execute("SHOW COLUMNS FROM journal_transactions LIKE 'category'")
            if not cursor.fetchone():
                cursor.execute("""
                    ALTER TABLE journal_transactions
                    ADD COLUMN category VARCHAR(50) DEFAULT '기타',
                    ADD COLUMN expected_sell_date DATE DEFAULT NULL,
                    ADD COLUMN target_sell_price DECIMAL(15,4) DEFAULT NULL,
                    ADD COLUMN strategy_memo TEXT DEFAULT NULL
                """)
                print("[Ver 6.2] journal_transactions columns added: category, expected_sell_date, target_sell_price, strategy_memo")
            else:
                print("[Ver 6.2] journal_transactions columns already exist")
            
            # Also add to managed_stocks for display
            cursor.execute("SHOW COLUMNS FROM managed_stocks LIKE 'category'")
            if not cursor.fetchone():
                cursor.execute("""
                    ALTER TABLE managed_stocks
                    ADD COLUMN category VARCHAR(50) DEFAULT '기타',
                    ADD COLUMN expected_sell_date DATE DEFAULT NULL,
                    ADD COLUMN target_sell_price DECIMAL(15,4) DEFAULT NULL,
                    ADD COLUMN strategy_memo TEXT DEFAULT NULL
                """)
                print("[Ver 6.2] managed_stocks columns added: category, expected_sell_date, target_sell_price, strategy_memo")
            else:
                print("[Ver 6.2] managed_stocks columns already exist")
                
        conn.commit()
        return True
    except Exception as e:
        print(f"Migration Error: {e}")
        return False
    finally:
        conn.close()

def delete_holding(ticker):
    """완전 삭제 (Delete from managed_stocks)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM managed_stocks WHERE ticker=%s", (ticker,))
        conn.commit()
        return True, "Deleted"
    except Exception as e:
        print(f"Delete Holding Error: {e}")
        return False, str(e)
    finally:
        conn.close()

def migrate_v63_add_is_holding():
    """[Ver 6.3] Add is_holding column to managed_stocks"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM managed_stocks LIKE 'is_holding'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE managed_stocks ADD COLUMN is_holding BOOLEAN DEFAULT TRUE")
                print("✅ Migration(v63): Added is_holding column")
    except Exception as e:
        print(f"Migration(v63) Error: {e}")
    finally:
        conn.close()

# [Ver 6.6] Migration: Add group_name to managed_stocks
def migrate_v64_add_group_name_to_managed_stocks():
    """Add group_name column to managed_stocks if missing"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM managed_stocks LIKE 'group_name'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE managed_stocks ADD COLUMN group_name VARCHAR(50) DEFAULT '기타'")
                print("✅ Migration(v64): Added group_name column to managed_stocks")
    except Exception as e:
        print(f"Migration(v64) Error: {e}")
    finally:
        conn.close()

# [Ver 6.6] Update Holding Info (Meta Data)
def update_holding_info(ticker, category=None, group_name=None, is_holding=None, target_sell_price=None, expected_sell_date=None, strategy_memo=None, manual_qty=None, manual_price=None):
    """Update metadata for a holding in managed_stocks"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check if record exists
            cursor.execute("SELECT ticker FROM managed_stocks WHERE ticker=%s", (ticker,))
            if not cursor.fetchone():
                # [Upsert Logic] Insert new record if not exists
                c2 = conn.cursor()
                c2.execute("SELECT name FROM stocks WHERE code=%s", (ticker,))
                s_row = c2.fetchone()
                c2.close()
                name = s_row['name'] if s_row else ticker
                
                cols = ["ticker", "name", "group_name", "category", "is_holding"]
                vals = ["%s", "%s", "%s", "%s", "%s"]
                # Default values
                p = [ticker, name, group_name or '기타', category or '기타', is_holding if is_holding is not None else True]
                
                if target_sell_price is not None:
                    cols.append("target_sell_price"); vals.append("%s"); p.append(target_sell_price)
                if expected_sell_date and expected_sell_date != '':
                    cols.append("expected_sell_date"); vals.append("%s"); p.append(expected_sell_date)
                if strategy_memo is not None:
                    cols.append("strategy_memo"); vals.append("%s"); p.append(strategy_memo)
                
                # [Ver 6.8] Simulation Fields
                if manual_qty is not None:
                    cols.append("manual_qty"); vals.append("%s"); p.append(manual_qty)
                if manual_price is not None:
                    cols.append("manual_price"); vals.append("%s"); p.append(manual_price)
                    
                sql = f"INSERT INTO managed_stocks ({', '.join(cols)}) VALUES ({', '.join(vals)})"
                cursor.execute(sql, p)
                conn.commit()
                return True, "Inserted successfully"

            # Dynamic Update
            fields = []
            params = []
            
            if category is not None:
                fields.append("category = %s")
                params.append(category)
            if group_name is not None:
                fields.append("group_name = %s")
                params.append(group_name)
            if is_holding is not None:
                fields.append("is_holding = %s")
                params.append(is_holding)
            
            # [New] Strategy Fields
            if target_sell_price is not None:
                fields.append("target_sell_price = %s")
                params.append(target_sell_price)
                
            if expected_sell_date is not None:
                if expected_sell_date == '': 
                    fields.append("expected_sell_date = NULL")
                else:
                    fields.append("expected_sell_date = %s")
                    params.append(expected_sell_date)
            
            if strategy_memo is not None:
                fields.append("strategy_memo = %s")
                params.append(strategy_memo)

            # [Ver 6.8] Simulation Fields
            if manual_qty is not None:
                fields.append("manual_qty = %s")
                params.append(manual_qty)
            if manual_price is not None:
                fields.append("manual_price = %s")
                params.append(manual_price)
            
            if not fields:
                return True, "No changes"
            
            params.append(ticker)
            sql = f"UPDATE managed_stocks SET {', '.join(fields)} WHERE ticker = %s"
            cursor.execute(sql, params)
        conn.commit()
        return True, "Updated"
    except Exception as e:
        print(f"Update Holding Info Error: {e}")
        return False, str(e)
        conn.close()

def migrate_v67_add_new_columns_to_managed_stocks():
    """Add category, target_sell_price, expected_sell_date, strategy_memo to managed_stocks if missing"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check and Add category
            cursor.execute("SHOW COLUMNS FROM managed_stocks LIKE 'category'")
            if not cursor.fetchone():
                print("Migrating: Adding category to managed_stocks")
                cursor.execute("ALTER TABLE managed_stocks ADD COLUMN category VARCHAR(50) DEFAULT '기타'")
                
            # Check and Add target_sell_price
            cursor.execute("SHOW COLUMNS FROM managed_stocks LIKE 'target_sell_price'")
            if not cursor.fetchone():
                print("Migrating: Adding target_sell_price to managed_stocks")
                cursor.execute("ALTER TABLE managed_stocks ADD COLUMN target_sell_price DECIMAL(18,2) NULL")
                
            # Check and Add expected_sell_date
            cursor.execute("SHOW COLUMNS FROM managed_stocks LIKE 'expected_sell_date'")
            if not cursor.fetchone():
                print("Migrating: Adding expected_sell_date to managed_stocks")
                cursor.execute("ALTER TABLE managed_stocks ADD COLUMN expected_sell_date DATE NULL")
                
            # Check and Add strategy_memo
            cursor.execute("SHOW COLUMNS FROM managed_stocks LIKE 'strategy_memo'")
            if not cursor.fetchone():
                print("Migrating: Adding strategy_memo to managed_stocks")
                cursor.execute("ALTER TABLE managed_stocks ADD COLUMN strategy_memo TEXT NULL")

            conn.commit()
    except Exception as e:
        print(f"Migration V67 Error: {e}")
    finally:
        try: conn.close()
        except: pass

def migrate_v68_add_simulation_columns():
    """Add manual_qty and manual_price to managed_stocks for Watchlist Simulation"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # manual_qty
            cursor.execute("SHOW COLUMNS FROM managed_stocks LIKE 'manual_qty'")
            if not cursor.fetchone():
                print("Migrating: Adding manual_qty to managed_stocks")
                cursor.execute("ALTER TABLE managed_stocks ADD COLUMN manual_qty INT DEFAULT 0")
            
            # manual_price
            cursor.execute("SHOW COLUMNS FROM managed_stocks LIKE 'manual_price'")
            if not cursor.fetchone():
                print("Migrating: Adding manual_price to managed_stocks")
                cursor.execute("ALTER TABLE managed_stocks ADD COLUMN manual_price DECIMAL(18,2) DEFAULT 0")
                
            conn.commit()
    except Exception as e:
        print(f"Migration V68 Error: {e}")
    finally:
        try: conn.close()
        except: pass
