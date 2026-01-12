import pymysql
from db import get_connection

def migrate_indicators_table():
    print("Migrating market_indicators_log table...")
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check if columns exist
            cursor.execute("SHOW COLUMNS FROM market_indicators_log LIKE 'score'")
            if not cursor.fetchone():
                print("Adding 'score' column...")
                cursor.execute("ALTER TABLE market_indicators_log ADD COLUMN score INT DEFAULT 0 COMMENT '종합 점수'")
            
            cursor.execute("SHOW COLUMNS FROM market_indicators_log LIKE 'evaluation'")
            if not cursor.fetchone():
                print("Adding 'evaluation' column...")
                cursor.execute("ALTER TABLE market_indicators_log ADD COLUMN evaluation VARCHAR(50) COMMENT '평가 등급'")
                
            cursor.execute("SHOW COLUMNS FROM market_indicators_log LIKE 'strategy_comment'")
            if not cursor.fetchone():
                print("Adding 'strategy_comment' column...")
                cursor.execute("ALTER TABLE market_indicators_log ADD COLUMN strategy_comment TEXT COMMENT 'Action Plan 텍스트'")
                
            cursor.execute("SHOW COLUMNS FROM market_indicators_log LIKE 'v2_state'")
            if not cursor.fetchone():
                print("Adding 'v2_state' column...")
                cursor.execute("ALTER TABLE market_indicators_log ADD COLUMN v2_state VARCHAR(50) COMMENT 'V2 단계 상태'")
            
            conn.commit()
            print("Migration completed successfully.")
            
    except Exception as e:
        print(f"Migration Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_indicators_table()
