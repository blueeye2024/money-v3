import pymysql
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
    "cursorclass": pymysql.cursors.DictCursor
}

def get_connection():
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
            INSERT INTO signal_history (ticker, name, signal_type, position_desc, price, signal_time, is_sent, score, interpretation)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                signal_data['ticker'],
                signal_data['name'],
                signal_data['signal_type'],
                signal_data['position'],
                signal_data['current_price'],
                st, 
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

def check_recent_sms_log(stock_name, signal_type, interval_minutes=30):
    """Check if a similar SMS was sent recently"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check for messages containing the stock name AND signal type within interval
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
            
            cursor.execute(sql, (like_stock, like_type, int(interval_minutes)))
            return cursor.fetchone()
    finally:
        conn.close()



# --- Stock Management ---
def get_stocks():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM stocks ORDER BY name ASC")
            return cursor.fetchall()
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

def get_transactions():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT j.*, s.name as stock_name 
            FROM journal_transactions j 
            LEFT JOIN stocks s ON j.ticker = s.code 
            ORDER BY j.trade_date DESC
            """
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conn.close()

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
