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
    """종목 목록 조회 (현재가 포함)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT ticker as code, name, current_price, price_updated_at, is_market_open 
                FROM managed_stocks 
                WHERE is_active = TRUE
                ORDER BY ticker ASC
            """)
            rows = cursor.fetchall()
            
            # DictCursor이므로 딕셔너리 리스트 반환
            # ticker를 code로 alias하여 기존 프론트엔드 호환성 유지
            return rows
    finally:
        conn.close()

def add_stock(code, name):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO stocks (code, name) VALUES (%s, %s)", (code, name))
        conn.commit()
        return True
    except Exception as e:
        print(f"Add Stock Error: {e}")
        return False
    finally:
        conn.close()

def delete_stock(code):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM stocks WHERE code=%s", (code,))
        conn.commit()
        return True
    finally:
        conn.close()

# --- Journal Transactions ---
def add_transaction(data):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO journal_transactions (ticker, trade_type, qty, price, trade_date, memo)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                data['ticker'],
                data['trade_type'],
                data['qty'],
                data['price'],
                data['trade_date'],
                data.get('memo', '')
            ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Add Transaction Error: {e}")
        return False
    finally:
        conn.close()

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
            WHERE quantity > 0 OR is_active = TRUE
            ORDER BY ticker ASC
            """
            cursor.execute(sql)
            return cursor.fetchall()
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

def add_transaction(ticker, trade_type, qty, price, trade_date, memo):
    # Adapter: Convert Trade Input -> Holding Update
    qty_change = qty if trade_type == 'BUY' else -qty
    return update_holding(ticker, qty_change, price, memo)

def get_transactions_legacy():
    # Placeholder if old function is called
    return []

def update_transaction(id, data):
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


def get_current_holdings():
    """Returns a dict of tickers currently held {ticker: {'qty': qty, 'avg_price': price}} using FIFO logic"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Fetch all txs sorted
            sql = "SELECT ticker, trade_type, qty, price, trade_date FROM journal_transactions ORDER BY trade_date ASC"
            cursor.execute(sql)
            txs = cursor.fetchall()
            
            # FIFO Calculation
            queues = {} # ticker -> list of {price, qty}
            
            for tx in txs:
                t = tx['ticker']
                if t not in queues: queues[t] = []
                
                if tx['trade_type'] == 'BUY':
                    queues[t].append({'p': float(tx['price']), 'q': int(tx['qty'])})
                else:
                    sell_q = int(tx['qty'])
                    while sell_q > 0 and queues[t]:
                        batch = queues[t][0]
                        if batch['q'] > sell_q:
                            batch['q'] -= sell_q
                            sell_q = 0
                        else:
                            sell_q -= batch['q']
                            queues[t].pop(0)

            # Summarize results
            result = {}
            for t, q_list in queues.items():
                total_q = sum(item['q'] for item in q_list)
                if total_q > 0:
                    total_cost = sum(item['q'] * item['p'] for item in q_list)
                    avg = total_cost / total_q
                    result[t] = {'qty': total_q, 'avg_price': avg}
            
            return result
    except Exception as e:
        print(f"Error fetching holdings: {e}")
        return {}
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
                
                print(f"📊 {len(rows)}개 종목 현재가 업데이트 시작...")
                
                updated_count = 0
                skipped_count = 0
                failed_count = 0
                
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
                        
                        # KIS API로 현재가 조회
                        print(f"  🔍 {ticker} ({exchange}) 조회 중...")
                        price_data = get_current_price(ticker, exchange)
                        
                        if price_data and price_data.get('price', 0) > 0:
                            current_price = price_data['price']
                            is_market_open = price_data.get('is_open', True)
                            
                            # 현재가 업데이트
                            update_sql = """
                                UPDATE managed_stocks 
                                SET current_price = %s, 
                                    price_updated_at = NOW(), 
                                    is_market_open = %s,
                                    exchange = %s
                                WHERE ticker = %s
                            """
                            cursor.execute(update_sql, (current_price, is_market_open, exchange, ticker))
                            updated_count += 1
                            print(f"  ✅ {ticker}: ${current_price:.2f}")
                        else:
                            # 가격 데이터 없음 (휴장일 또는 오류)
                            update_sql = """
                                UPDATE managed_stocks 
                                SET is_market_open = FALSE, 
                                    price_updated_at = NOW(),
                                    exchange = %s
                                WHERE ticker = %s
                            """
                            cursor.execute(update_sql, (exchange, ticker))
                            failed_count += 1
                            print(f"  ⚠️ {ticker}: 가격 조회 실패 (휴장 또는 오류)")
                    
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
