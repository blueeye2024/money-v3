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


def log_market_indicators(data):
    """
    시장 지표 및 신호 상태 DB 저장
    data struct: {
        'ticker': str,
        'candle_time': datetime (NY),
        'rsi': float, 'vr': float, 'atr': float, 'pivot_r1': float,
        'gold_30m': str ('N' or 'YYYY-MM-DD HH:MM:SS'),
        ...
    }
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO market_indicators_log 
            (ticker, candle_time, rsi_14, vol_ratio, atr, pivot_r1, gold_30m, gold_5m, dead_30m, dead_5m)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                data['ticker'], data['candle_time'], 
                data.get('rsi', 0), data.get('vr', 0), data.get('atr', 0), data.get('pivot_r1', 0),
                data.get('gold_30m', 'N'), data.get('gold_5m', 'N'),
                data.get('dead_30m', 'N'), data.get('dead_5m', 'N')
            ))
            conn.commit()
    except Exception as e:
        print(f"Log Indicators Error: {e}")
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
            sql_stocks = """
            CREATE TABLE IF NOT EXISTS stocks (
                code VARCHAR(10) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql_stocks)

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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticker) REFERENCES stocks(code) ON DELETE CASCADE
            )
            """
            cursor.execute(sql_journal)

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

            # --- Seed Initial Data ---
            # Seed Managed Stocks
            initial_stocks = [
                ('SOXL', '초고성장/레버리지', 'SMA 10/30 골든크로스 + 박스권 10% 돌파 + 거래량 250%↑', '(5분봉) EMA 9/21 데드크로스 시 70% 익절, 30분봉 데드크로스 시 전량 매도', 25),
                ('IONQ', '초고성장/레버리지', 'SMA 10/30 골든크로스 + 박스권 15% 돌파 + 거래량 300%↑', '고점 대비 10% 하락 시 즉시 매도 (Chandelier Exit), 손절 -8%', 15),
                ('TSLA', '초고성장/레버리지', 'SMA 10/30 골든크로스 + 박스권 5% 돌파 + RSI 60 이상', '30분봉 SMA 10선 종가 이탈 시 매도, 손절 -4%', 15),
                ('UPRO', '지수 및 헷지', 'EMA 15/50 골든크로스 + 박스권 8% 돌파 + EMA 200 필터', '30분봉 EMA 15/50 데드크로스 또는 손절 -6%', 25),
                ('TMF', '지수 및 헷지', 'EMA 15/50 골든크로스 + 박스권 4% 돌파 (UPRO 하락 시 비중 2배)', '30분봉 EMA 15/50 데드크로스 또는 손절 -4.5%', 5),
                ('SOXS', '지수 및 헷지', 'UPRO < 일봉 EMA 200일 때만 가동 + 30분봉 골든크로스', '수익 5% 도달 시 전량 익절, 24시간 내 미수익 시 타임컷 종료', 0),
                ('GOOGL', '안정성/우량주', 'EMA 15/50 골든크로스 + RSI 50 이상 유지', '5분봉 SMA 20선 추격 매도 (Trailing Stop), 손절 -4%', 5),
                ('AAAU', '안정성/우량주', 'EMA 10/40 골든크로스 (반응성 강화)', '30분봉 EMA 10/40 데드크로스 또는 손절 -3%', 10),
                ('UFO', '안정성/우량주', '일봉 SMA 200 위에서만 가동 + 30분봉 SMA 10/30 골든크로스', '30분봉 SMA 30선 이탈 시 매도, 손절 -5%', 5)
            ]
            
            for stock in initial_stocks:
                # Upsert
                sql_seed = """
                INSERT INTO managed_stocks (ticker, group_name, buy_strategy, sell_strategy, target_ratio)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    group_name=VALUES(group_name), 
                    buy_strategy=VALUES(buy_strategy), 
                    sell_strategy=VALUES(sell_strategy),
                    target_ratio=VALUES(target_ratio)
                """
                cursor.execute(sql_seed, stock)

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
    """종목 목록 조회 (관리용, 모든 상태 반환)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT ticker as code, name, current_price, price_updated_at, is_market_open, is_active
                FROM managed_stocks 
                ORDER BY ticker ASC
            """)
            rows = cursor.fetchall()
            return rows
    finally:
        conn.close()

def add_stock(code, name, is_active=True):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # managed_stocks에 추가 (이미 존재하면 is_active 업데이트)
            sql = """
            INSERT INTO managed_stocks (ticker, name, is_active) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                name = VALUES(name),
                is_active = VALUES(is_active)
            """
            cursor.execute(sql, (code, name, is_active))
        conn.commit()
        return True
    except Exception as e:
        print(f"Add Stock Error: {e}")
        return False
    finally:
        conn.close()

def update_stock_status(code, is_active):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE managed_stocks SET is_active=%s WHERE ticker=%s", (is_active, code))
        conn.commit()
        return True
    except Exception as e:
        print(f"Update Stock Status Error: {e}")
        return False
    finally:
        conn.close()

def delete_stock(code):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
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
            SELECT ticker, name, quantity as qty, avg_price, current_price, is_market_open, is_manual_price
            FROM managed_stocks 
            WHERE quantity > 0
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

def update_holding(ticker, qty_change, price, memo=None):
    """보유량 및 평단가 업데이트 (매수/매도)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 기존 보유량 조회
            cursor.execute("SELECT quantity, avg_price FROM managed_stocks WHERE ticker=%s", (ticker,))
            row = cursor.fetchone()
            
            if not row:
                # 종목이 없으면 먼저 생성 (add_stock 호출 권장하지만 여기서도 처리 가능)
                return False, "Managed stock not found. Add stock first."
            
            current_qty = row['quantity'] or 0
            current_avg = row['avg_price'] or 0.0
            
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
            
            cursor.execute("""
                UPDATE managed_stocks 
                SET quantity=%s, avg_price=%s
                WHERE ticker=%s
            """, (new_qty, new_avg, ticker))
            
            conn.commit()
            return True, "Holding updated"
    except Exception as e:
        print(f"Update Holding Error: {e}")
        return False, str(e)
    finally:
        conn.close()

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
    else:
        ticker = ticker_or_data
        qty = int(qty) if qty else 0
        price = float(price) if price else 0

    # 1. Insert into journal_transactions (Source of Truth for Analysis)
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO journal_transactions 
            (ticker, trade_type, qty, price, trade_date, memo)
            VALUES (%s, %s, %s, %s, COALESCE(%s, NOW()), %s)
            """
            cursor.execute(sql, (ticker, trade_type, qty, price, trade_date, memo))
            conn.commit()
    except Exception as e:
        print(f"Insert Transaction Error: {e}")
    finally:
        conn.close()

    # 2. Update Managed Stocks (Snapshot for Frontend)
    if trade_type == 'RESET':
        return update_holding(ticker, qty, price, memo, is_reset=True)
    else:
        qty_change = qty if trade_type == 'BUY' else -qty
        return update_holding(ticker, qty_change, price, memo, is_reset=False)

def update_transaction(id, data):
    # Backward compatibility: For now, we just update journal_transactions log.
    # Recalculating holdings from history is complex.
    # Recommendation: User should use RESET to correct holdings.
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            UPDATE journal_transactions 
            SET ticker=%s, trade_type=%s, qty=%s, price=%s, trade_date=%s, memo=%s
            WHERE id=%s
            """
            cursor.execute(sql, (
                data['ticker'],
                data['trade_type'],
                data['qty'],
                data['price'],
                data['trade_date'],
                data.get('memo', ''),
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

def update_holding(ticker, qty_change_or_new_qty, price, memo=None, is_reset=False):
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
            
            cursor.execute("""
                UPDATE managed_stocks 
                SET quantity=%s, avg_price=%s
                WHERE ticker=%s
            """, (new_qty, new_avg, ticker))
            
            conn.commit()
            return True, "Holding updated"
    except Exception as e:
        print(f"Update Holding Error: {e}")
        return False, str(e)
    finally:
        conn.close()
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            UPDATE journal_transactions 
            SET ticker=%s, trade_type=%s, qty=%s, price=%s, trade_date=%s, memo=%s
            WHERE id=%s
            """
            cursor.execute(sql, (
                data['ticker'],
                data['trade_type'],
                data['qty'],
                data['price'],
                data['trade_date'],
                data.get('memo', ''),
                id
            ))
        conn.commit()
        return True
    finally:
        conn.close()

        conn.close()

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
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # Take last 100 candles to limit DB size
                recent = candles_df.tail(100)
                
                for idx, row in recent.iterrows():
                    sql = """
                    INSERT INTO candle_data (ticker, timeframe, candle_time, open, high, low, close, volume)
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
                        ticker, timeframe,
                        idx.to_pydatetime().replace(microsecond=0),
                        float(row['Open']),
                        float(row['High']),
                        float(row['Low']),
                        float(row['Close']),
                        int(row['Volume']) if 'Volume' in row else 0
                    ))
            conn.commit()
    except Exception as e:
        print(f"Save Candle Data Error ({ticker}/{timeframe}): {e}")

def get_candle_data(ticker, timeframe, limit=100):
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
                WHERE ticker=%s AND timeframe=%s
                ORDER BY candle_time DESC
                LIMIT %s
                """
                cursor.execute(sql, (ticker, timeframe, limit))
                rows = cursor.fetchall()
                
                if rows:
                    df = pd.DataFrame(rows)
                    df['candle_time'] = pd.to_datetime(df['candle_time'])
                    df = df.set_index('candle_time').sort_index()
                    df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                    return df
    except Exception as e:
        print(f"Get Candle Data Error ({ticker}/{timeframe}): {e}")
    return None

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
        print(f"Error getting last candle time: {e}")
        return None

def save_market_candles(ticker, timeframe, df, source='yfinance'):
    """Save DataFrame to market_candles table (Upsert)"""
    import pandas as pd
    if df is None or df.empty: return False
    
    try:
        with get_connection() as conn:
            data = []
            for idx, row in df.iterrows():
                if 'Open' not in row: continue
                # Handle potential timezone aware index
                ts = idx.to_pydatetime() if hasattr(idx, 'to_pydatetime') else idx
                if hasattr(ts, 'tzinfo') and ts.tzinfo:
                   # Convert to naive or UTC? DB is usually naive datetime.
                   # Assuming KST or UTC consistent. Let's strip tz or ensure it's correct.
                   ts = ts.replace(tzinfo=None)
                
                # CRITICAL: Normalize 1d candles to 00:00:00 for date-only comparison
                if timeframe == '1d':
                    ts = ts.replace(hour=0, minute=0, second=0, microsecond=0)

                vol = row.get('Volume', 0)
                if pd.isna(vol): vol = 0
                
                # Helper to handle NaN for MySQL
                def clean_val(v):
                    return None if pd.isna(v) else float(v)

                data.append((
                    ticker, timeframe, ts,
                    clean_val(row['Open']), clean_val(row['High']), 
                    clean_val(row['Low']), clean_val(row['Close']),
                    int(vol), source
                ))
                
            if not data: return False
            
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO market_candles (ticker, timeframe, candle_time, open_price, high_price, low_price, close_price, volume, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        open_price=VALUES(open_price), high_price=VALUES(high_price),
                        low_price=VALUES(low_price), close_price=VALUES(close_price),
                        volume=VALUES(volume), source=VALUES(source)
                """
                cursor.executemany(sql, data)
            conn.commit()
            return True
    except Exception as e:
        print(f"Error saving market candles ({ticker}): {e}")
        return False

def load_market_candles(ticker, timeframe, limit=300):
    """Load candles from DB as DataFrame"""
    import pandas as pd
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # Fetch limited DESC then sort ASC for latest N candles
                sql = f"""
                    SELECT * FROM (
                        SELECT candle_time, open_price as Open, high_price as High, 
                               low_price as Low, close_price as Close, volume as Volume
                        FROM market_candles 
                        WHERE ticker=%s AND timeframe=%s 
                        ORDER BY candle_time DESC LIMIT {limit}
                    ) sub ORDER BY candle_time ASC
                """
                
                cursor.execute(sql, (ticker, timeframe))
                rows = cursor.fetchall()
                
                if not rows: return None
                
                df = pd.DataFrame(rows)
                df['candle_time'] = pd.to_datetime(df['candle_time'])
                df.set_index('candle_time', inplace=True)
                
                # IMPORTANT: Data Integrity Fix
                # Fill missing values (None from DB) with interpolation
                # This prevents analysis logic from failing due to empty cells
                cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                for c in cols:
                    if c in df.columns:
                        df[c] = pd.to_numeric(df[c], errors='coerce')
                
                df = df.interpolate(method='time', limit_direction='both')
                if df.isnull().values.any():
                    df = df.ffill().bfill() # Fallback for edge cases
                
                return df
            
    except Exception as e:
        print(f"Error loading market candles: {e}")
        return None

def cleanup_old_candles(ticker, days=30):
    """Delete candles older than N days (Default 30)"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                sql = "DELETE FROM market_candles WHERE ticker=%s AND candle_time < DATE_SUB(NOW(), INTERVAL %s DAY)"
                cursor.execute(sql, (ticker, days))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error cleaning up old candles ({ticker}): {e}")
        return False

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
    from kis_api import get_current_price, get_exchange_code
    
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

                        # 1. KIS API로 현재가 조회
                        # print(f"  🔍 {ticker} ({exchange}) 조회 중... (KIS)")
                        price_data = get_current_price(ticker, exchange)
                        
                        if price_data and price_data.get('price', 0) > 0:
                            current_price = price_data['price']
                            is_market_open = price_data.get('is_open', True)
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
                                else:
                                    source = "YF(Fast)" # Fallback to last close
                                
                                if last_price > 0:
                                    current_price = last_price
                                    is_market_open = True # Assume open if we got data? Or derived path.
                            except Exception as ey:
                                print(f"  ❌ YF Fallback Failed: {ey}")
                        
                        if current_price > 0:
                            # 현재가 업데이트
                            update_sql = """
                                UPDATE managed_stocks 
                                SET current_price = %s, 
                                    price_updated_at = NOW(),
                                    is_market_open = %s
                                WHERE ticker = %s
                            """
                            cursor.execute(update_sql, (current_price, is_market_open, ticker))
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
                VALUES (%s, %s, %s, 'OPEN', '3.5.0')
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
                ORDER BY idx DESC LIMIT 1
            """
            cursor.execute(sql, (ticker,))
            return cursor.fetchone()
    finally:
        conn.close()

def save_v2_buy_signal(manage_id, ticker, signal_type, price):
    """매수 신호 단계별 업데이트 (1차, 2차, 3차)"""
    # signal_type: 'sig1', 'sig2', 'sig3', 'final'
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Check if record exists
            cursor.execute("SELECT idx FROM buy_stock WHERE manage_id=%s", (manage_id,))
            row = cursor.fetchone()
            
            if not row:
                # Insert New (Manage ID should be created by Caller if new)
                if signal_type == 'sig1':
                    sql = """
                        INSERT INTO buy_stock (manage_id, ticker, buy_sig1_yn, buy_sig1_price, buy_sig1_dt, row_dt)
                        VALUES (%s, %s, 'Y', %s, NOW(), NOW())
                    """
                    cursor.execute(sql, (manage_id, ticker, price))
                else:
                    return False # Cannot start with sig2/3 without record (logic dependency)
            else:
                # Update Existing
                if signal_type == 'sig1':
                     sql = "UPDATE buy_stock SET buy_sig1_yn='Y', buy_sig1_price=%s, buy_sig1_dt=NOW(), row_dt=NOW() WHERE manage_id=%s"
                elif signal_type == 'sig2':
                     sql = "UPDATE buy_stock SET buy_sig2_yn='Y', buy_sig2_price=%s, buy_sig2_dt=NOW(), row_dt=NOW() WHERE manage_id=%s"
                elif signal_type == 'sig3':
                     sql = "UPDATE buy_stock SET buy_sig3_yn='Y', buy_sig3_price=%s, buy_sig3_dt=NOW(), row_dt=NOW() WHERE manage_id=%s"
                elif signal_type == 'final':
                     sql = "UPDATE buy_stock SET final_buy_yn='Y', final_buy_price=%s, final_buy_dt=NOW(), row_dt=NOW() WHERE manage_id=%s"
                
                cursor.execute(sql, (price, manage_id))
                
        conn.commit()
        return True
    except Exception as e:
        print(f"Save Buy Signal Error: {e}")
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
                ORDER BY idx DESC LIMIT 1
            """
            cursor.execute(sql, (ticker,))
            return cursor.fetchone()
    finally:
        conn.close()

def create_v2_sell_record(manage_id, ticker, entry_price):
    """최종 진입 확정 시 sell_stock 레코드 생성"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO sell_stock (manage_id, ticker, final_sell_price, row_dt)
                VALUES (%s, %s, 0, NOW())
            """
            cursor.execute(sql, (manage_id, ticker))
        conn.commit()
        return True
    except Exception as e:
        print(f"Create Sell Record Error: {e}")
        return False
    finally:
        conn.close()

def save_v2_buy_signal(manage_id, signal_type, price):
    """매수 신호 단계별 업데이트"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = ""
            if signal_type == 'sig1':
                 sql = "UPDATE buy_stock SET buy_sig1_yn='Y', buy_sig1_price=%s, buy_sig1_dt=NOW() WHERE manage_id=%s"
            elif signal_type == 'sig2':
                 sql = "UPDATE buy_stock SET buy_sig2_yn='Y', buy_sig2_price=%s, buy_sig2_dt=NOW() WHERE manage_id=%s"
            elif signal_type == 'sig3':
                 sql = "UPDATE buy_stock SET buy_sig3_yn='Y', buy_sig3_price=%s, buy_sig3_dt=NOW() WHERE manage_id=%s"
            elif signal_type == 'final':
                 sql = "UPDATE buy_stock SET final_buy_yn='Y', final_buy_price=%s, final_buy_dt=NOW() WHERE manage_id=%s"
            
            if sql:
                cursor.execute(sql, (price, manage_id))
                conn.commit()
                return True
            return False
    except Exception as e:
        print(f"Save Buy Signal Error: {e}")
        return False
    finally:
        conn.close()

def save_v2_sell_signal(manage_id, signal_type, price):
    """청산 신호 단계별 업데이트"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            if signal_type == 'sig1':
                 sql = "UPDATE sell_stock SET sell_sig1_yn='Y', sell_sig1_price=%s, sell_sig1_dt=NOW() WHERE manage_id=%s"
            elif signal_type == 'sig2':
                 sql = "UPDATE sell_stock SET sell_sig2_yn='Y', sell_sig2_price=%s, sell_sig2_dt=NOW() WHERE manage_id=%s"
            elif signal_type == 'sig3':
                 sql = "UPDATE sell_stock SET sell_sig3_yn='Y', sell_sig3_price=%s, sell_sig3_dt=NOW() WHERE manage_id=%s"
            elif signal_type == 'final':
                 sql = "UPDATE sell_stock SET final_sell_yn='Y', final_sell_price=%s, final_sell_dt=NOW() WHERE manage_id=%s"
            
            cursor.execute(sql, (price, manage_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Save Sell Signal Error: {e}")
        return False
    finally:
        conn.close()

def update_v2_target_price(manage_id, target_type, price):
    """Set custom target price for Box(Buy2) or Stop(Sell2)"""
    # target_type: 'box' or 'stop'
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            if target_type == 'box':
                sql = "UPDATE buy_stock SET target_box_price=%s WHERE manage_id=%s"
            elif target_type == 'stop':
                sql = "UPDATE sell_stock SET target_stop_price=%s WHERE manage_id=%s"
            else:
                return False
            
            cursor.execute(sql, (price, manage_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Update Target Price Error: {e}")
        return False
    finally:
        conn.close()

def confirm_v2_buy(manage_id, price, qty):
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
                    real_buy_dt = NOW()
                WHERE manage_id = %s
            """
            cursor.execute(sql, (price, qty, manage_id))
            
            # Log
            log_history(manage_id, 'SOXS', '실매수확정', f"가격:${price}/수량:{qty}", price)
            
        conn.commit()
        return True, "Success"
    except Exception as e:
        print(f"Confirm V2 Buy Error: {e}")
        return False, str(e)
    finally:
        conn.close()

def confirm_v2_sell(manage_id, price, qty, is_end=False):
    """사용자 실제 매도(청산) 확정 입력"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # If is_end=True, we close the cycle (close_yn='Y')
            close_flag = 'Y' if is_end else 'N'
            
            if is_end:
                # Terminate Trade: Set final flags
                sql = """
                    UPDATE sell_stock
                    SET real_hold_yn = 'N', 
                        real_sell_avg_price = %s,
                        real_sell_qn = %s,
                        real_sell_dt = NOW(),
                        close_yn = 'Y',
                        final_sell_yn = 'Y'
                    WHERE manage_id = %s
                """
                cursor.execute(sql, (price, qty, manage_id))
                
                # Also Close BUY Record (final_buy_yn = 'Y') to allow new cycle
                sql_buy = "UPDATE buy_stock SET final_buy_yn = 'Y', row_dt = NOW() WHERE manage_id = %s"
                cursor.execute(sql_buy, (manage_id,))
                
                log_history(manage_id, 'SYSTEM', '미션종료', f"최종청산: ${price} / {qty}개", price)
            else:
                # Partial Update: Just update info, keep holding
                sql = """
                    UPDATE sell_stock
                    SET real_sell_avg_price = %s,
                        real_sell_qn = %s,
                        real_sell_dt = NOW()
                    WHERE manage_id = %s
                """
                cursor.execute(sql, (price, qty, manage_id))
                log_history(manage_id, 'SYSTEM', '중간청산', f"수량/금액 업데이트", price)

            if cursor.rowcount == 0:
                 return False, "참조하는 매매 데이터(ManageID)를 찾을 수 없습니다."

        conn.commit()
        return True, "Success"
    except Exception as e:
        print(f"Confirm V2 Sell Error: {e}")
        return False, str(e)
    finally:
        conn.close()

def manual_update_signal(manage_id, signal_key, price, status='Y', ticker=None):
    """
    수동으로 신호 상태 변경 (1차, 2차, 3차)
    signal_key: 'buy1', 'buy2', 'buy3', 'sell1', 'sell2', 'sell3'
    status: 'Y' (Set) or 'N' (Cancel)
    ticker: Optional, used to create new record if not exists
    """
    conn = get_connection()
    try:
        # Map key to columns
        mapping = {
            'buy1': ('buy_stock', 'buy_sig1_yn', 'buy_sig1_price', 'buy_sig1_dt'),
            'buy2': ('buy_stock', 'buy_sig2_yn', 'buy_sig2_price', 'buy_sig2_dt'),
            'buy3': ('buy_stock', 'buy_sig3_yn', 'buy_sig3_price', 'buy_sig3_dt'),
            'sell1': ('sell_stock', 'sell_sig1_yn', 'sell_sig1_price', 'sell_sig1_dt'),
            'sell2': ('sell_stock', 'sell_sig2_yn', 'sell_sig2_price', 'sell_sig2_dt'),
            'sell3': ('sell_stock', 'sell_sig3_yn', 'sell_sig3_price', 'sell_sig3_dt')
        }
        
        if signal_key not in mapping:
            return False
            
        table, col_yn, col_price, col_dt = mapping[signal_key]
        
        with conn.cursor() as cursor:
            # Check existence first
            check_sql = f"SELECT 1 FROM {table} WHERE manage_id=%s"
            cursor.execute(check_sql, (manage_id,))
            exists = cursor.fetchone()
            
            if not exists:
                if ticker and table == 'buy_stock' and status == 'Y':
                    # Create New Record
                    # Note: For sell_stock, user should terminate buy first or we need buy record logic? 
                    # If auto creating sell, we need entry price? 
                    # For now only support auto-create BUY cycle.
                    sql_insert = f"""
                        INSERT INTO buy_stock (manage_id, ticker, row_dt, {col_yn}, {col_price}, {col_dt})
                        VALUES (%s, %s, NOW(), %s, %s, NOW())
                    """
                    cursor.execute(sql_insert, (manage_id, ticker, status, price))
                    log_history(manage_id, ticker, '수동신호생성', f"Manual Start {signal_key}", price)
                    # Commit via main flow
                else:
                    print(f"Manual Update Skipped: Record not found for {manage_id} (Ticker={ticker})")
                    return False
            else:
                # Update existing
                sql = f"""
                    UPDATE {table}
                    SET {col_yn} = %s, 
                        {col_price} = %s, 
                        {col_dt} = NOW()
                    WHERE manage_id = %s
                """
                cursor.execute(sql, (status, price, manage_id))
            
            # [FIX] Clear Custom Targets when Resetting Signal 2
            if status == 'N':
                if signal_key == 'buy2':
                    cursor.execute(f"UPDATE {table} SET target_box_price = NULL WHERE manage_id=%s", (manage_id,))
                    log_history(manage_id, ticker, 'SYSTEM', '목표가 초기화(Buy)', 0)
                elif signal_key == 'sell2':
                    cursor.execute(f"UPDATE {table} SET target_stop_price = NULL WHERE manage_id=%s", (manage_id,))
                    log_history(manage_id, ticker, 'SYSTEM', '목표가 초기화(Sell)', 0)

            # Logic for final_buy only if status is 'Y'
            if status == 'Y' and signal_key == 'buy3':
                 cursor.execute("UPDATE buy_stock SET final_buy_yn='Y', final_buy_price=%s, final_buy_dt=NOW() WHERE manage_id=%s", (price, manage_id))
            
            # Log
            log_ticker = ticker if ticker else 'SOXS' # fallback if not passed (though existence implies we might know it, but DB doesn't select it)
            if exists: # Try to fetch ticker if exists to log correctly? 
                 # For efficiency skip fetching ticker if not sure.
                 pass
            
            log_history(manage_id, log_ticker, '수동신호변경', f"{signal_key}:{status}", price)
            
        conn.commit()
        return True
    except Exception as e:
        print(f"Manual Update Error: {e}")
        return False
    finally:
        conn.close()

def delete_v2_record(manage_id):
    """기록 삭제 (전체 - 매수+매도)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Delete from buy_stock and sell_stock
            cursor.execute("DELETE FROM buy_stock WHERE manage_id = %s", (manage_id,))
            cursor.execute("DELETE FROM sell_stock WHERE manage_id = %s", (manage_id,))
            
            log_history(manage_id, 'SOXS', '기록삭제(전체)', 'User Request (All)', 0)
            
        conn.commit()
        return True
    except Exception as e:
        print(f"Delete Record Error: {e}")
        return False
    finally:
        conn.close()

def delete_v2_sell_only(manage_id):
    """매도(Sell) 기록만 삭제 (매수는 유지 - 다시 매도 사이클 시작 가능)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM sell_stock WHERE manage_id = %s", (manage_id,))
            log_history(manage_id, 'SOXS', '매도기록삭제', 'User Request (Sell Only)', 0)
        conn.commit()
        return True
    except Exception as e:
        print(f"Delete Sell Only Error: {e}")
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
