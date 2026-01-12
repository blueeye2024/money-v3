import pymysql
from db import get_connection

def migrate_v2():
    print("Starting Migration V2: Snapshot & History Split...")
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Rename existing log table to history
            # Check if history already exists to avoid error
            cursor.execute("SHOW TABLES LIKE 'market_indicators_history'")
            if not cursor.fetchone():
                cursor.execute("SHOW TABLES LIKE 'market_indicators_log'")
                if cursor.fetchone():
                    print("Renaming market_indicators_log -> market_indicators_history")
                    cursor.execute("RENAME TABLE market_indicators_log TO market_indicators_history")
                else:
                    print("Warning: market_indicators_log not found. Creating new history table.")
                    sql_hist = """
                    CREATE TABLE market_indicators_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        ticker VARCHAR(10) NOT NULL,
                        candle_time DATETIME NOT NULL,
                        rsi_14 DECIMAL(10, 2),
                        vol_ratio DECIMAL(10, 2),
                        atr DECIMAL(10, 4),
                        pivot_r1 DECIMAL(10, 2),
                        gold_30m VARCHAR(30) DEFAULT 'N',
                        gold_5m VARCHAR(30) DEFAULT 'N',
                        dead_30m VARCHAR(30) DEFAULT 'N',
                        dead_5m VARCHAR(30) DEFAULT 'N',
                        score INT DEFAULT 0 COMMENT '종합 점수',
                        evaluation VARCHAR(50) COMMENT '평가 등급',
                        strategy_comment TEXT COMMENT '자세한 분석 내용',
                        v2_state VARCHAR(50) COMMENT 'V2 상태',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                    cursor.execute(sql_hist)
            
            # 2. Create Snapshot Table
            cursor.execute("SHOW TABLES LIKE 'market_indicators_snapshot'")
            if not cursor.fetchone():
                print("Creating market_indicators_snapshot table...")
                sql_snap = """
                CREATE TABLE market_indicators_snapshot (
                    ticker VARCHAR(10) PRIMARY KEY,
                    candle_time DATETIME NOT NULL,
                    rsi_14 DECIMAL(10, 2),
                    vol_ratio DECIMAL(10, 2),
                    atr DECIMAL(10, 4),
                    pivot_r1 DECIMAL(10, 2),
                    gold_30m VARCHAR(30) DEFAULT 'N',
                    gold_5m VARCHAR(30) DEFAULT 'N',
                    dead_30m VARCHAR(30) DEFAULT 'N',
                    dead_5m VARCHAR(30) DEFAULT 'N',
                    score INT DEFAULT 0 COMMENT '종합 점수',
                    evaluation VARCHAR(50) COMMENT '평가 등급',
                    strategy_comment TEXT COMMENT '자세한 분석 내용',
                    v2_state VARCHAR(50) COMMENT 'V2 상태',
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
                cursor.execute(sql_snap)

            conn.commit()
            print("Migration V2 Completed Successfully.")

    except Exception as e:
        print(f"Migration V2 Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_v2()
