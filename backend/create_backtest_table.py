
import pymysql

# Connection Config (from db.py)
DB_CONFIG = {
    "host": "114.108.180.228",
    "port": 3306,
    "user": "blueeye",
    "password": "blueeye0037!",
    "database": "mywork_01",
    "charset": "utf8mb4"
}

def create_table():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            # Check if table exists
            cursor.execute("SHOW TABLES LIKE 'backtest_results'")
            if cursor.fetchone():
                print("ℹ️ Table 'backtest_results' already exists.")
                # Optional: Drop it? No, keep it. User might want history.
                # Or maybe user wants fresh start each time? "Table is added for use".
                # I'll ensure columns are correct if I were updating, but for now just create if not exists.
            else:
                print("Creating 'backtest_results' table...")
                sql = """
                CREATE TABLE backtest_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    simulation_id VARCHAR(50) NOT NULL,
                    ticker VARCHAR(10) NOT NULL,
                    candle_time DATETIME NOT NULL,
                    price DECIMAL(10, 2),
                    change_pct DECIMAL(10, 2),
                    total_score FLOAT,
                    cheongan_score FLOAT,
                    rsi DECIMAL(10, 2),
                    macd DECIMAL(10, 4),
                    vol_ratio DECIMAL(10, 2),
                    atr DECIMAL(10, 4),
                    bbi DECIMAL(10, 2),
                    signal_step TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_sim_id (simulation_id),
                    INDEX idx_ticker_time (ticker, candle_time)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
                cursor.execute(sql)
                conn.commit()
                print("✅ Table 'backtest_results' created successfully.")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_table()
