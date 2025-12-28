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
            
            # 2. Trading Journal Table (User manual entry)
            sql_journal = """
            CREATE TABLE IF NOT EXISTS trading_journal (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10) NOT NULL,
                stock_name VARCHAR(100),
                entry_date DATETIME,
                exit_date DATETIME,
                entry_price DECIMAL(10, 2),
                exit_price DECIMAL(10, 2),
                quantity INT,
                profit_loss DECIMAL(15, 2),
                profit_pct DECIMAL(10, 2),
                reason TEXT,
                status VARCHAR(20) DEFAULT 'OPEN', -- OPEN, CLOSED
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql_journal)
            
        conn.commit()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"DB Initialization Error: {e}")
    finally:
        conn.close()

def save_signal(signal_data):
    """Save a detected signal to DB"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO signal_history (ticker, name, signal_type, position_desc, price, signal_time, is_sent)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                signal_data['ticker'],
                signal_data['name'],
                signal_data['signal_type'],
                signal_data['position'],
                signal_data['current_price'],
                signal_data['signal_time_raw'], # Expecting datetime object
                signal_data.get('is_sent', False)
            ))
        conn.commit()
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

# Journal Functions
def add_journal_entry(data):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Calculate Profit if exit exists
            profit_loss = 0
            profit_pct = 0
            status = 'OPEN'
            
            if data.get('exit_price') and data.get('exit_date'):
                entry = float(data['entry_price'])
                exit_p = float(data['exit_price'])
                qty = int(data['quantity'])
                profit_loss = (exit_p - entry) * qty
                profit_pct = ((exit_p - entry) / entry) * 100
                status = 'CLOSED'
            
            sql = """
            INSERT INTO trading_journal 
            (ticker, stock_name, entry_date, entry_price, quantity, reason, status, exit_date, exit_price, profit_loss, profit_pct)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                data['ticker'],
                data.get('stock_name', ''),
                data['entry_date'],
                data['entry_price'],
                data['quantity'],
                data['reason'],
                status,
                data.get('exit_date'),
                data.get('exit_price'),
                profit_loss,
                profit_pct
            ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Journal Insert Error: {e}")
        return False
    finally:
        conn.close()

def get_journal_entries():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM trading_journal ORDER BY entry_date DESC"
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conn.close()
