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

def delete_transaction(id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM journal_transactions WHERE id=%s", (id,))
        conn.commit()
        return True
    finally:
        conn.close()

def get_current_holdings():
    """Returns a list of tickers currently held (Net Qty > 0)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT ticker, 
                   SUM(CASE WHEN trade_type = 'BUY' THEN qty 
                            WHEN trade_type = 'SELL' THEN -qty 
                            ELSE 0 END) as net_qty
            FROM journal_transactions
            GROUP BY ticker
            HAVING net_qty > 0
            """
            cursor.execute(sql)
            results = cursor.fetchall()
            return [row['ticker'] for row in results]
    except Exception as e:
        print(f"Error fetching holdings: {e}")
        return []
    finally:
        conn.close()
