"""
자산 관리 및 전략 평가 시스템 DB 마이그레이션
Phase 1: daily_assets, trading_strategies 테이블 생성
"""

import pymysql

DB_CONFIG = {
    "host": "114.108.180.228",
    "port": 3306,
    "user": "blueeye",
    "password": "blueeye0037!",
    "database": "mywork_01",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

def migrate_db():
    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("=" * 60)
        print("🚀 자산 관리 및 전략 평가 시스템 DB 마이그레이션 시작")
        print("=" * 60)

        # 1. daily_assets 테이블 생성
        print("\n📊 [1/3] daily_assets 테이블 생성 중...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_assets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                record_date DATE NOT NULL,
                total_assets DECIMAL(15,2) NOT NULL COMMENT '총 자산 (USD)',
                cash_balance DECIMAL(15,2) DEFAULT 0 COMMENT '현금 잔고',
                stock_value DECIMAL(15,2) DEFAULT 0 COMMENT '주식 평가액',
                daily_change DECIMAL(15,2) DEFAULT 0 COMMENT '전일 대비 증감액',
                daily_change_pct DECIMAL(8,4) DEFAULT 0 COMMENT '전일 대비 증감률 (%)',
                note TEXT COMMENT '메모',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_date (record_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='일별 자산 기록'
        """)
        print("   ✅ daily_assets 테이블 생성 완료")

        # 2. trading_strategies 테이블 생성
        print("\n📋 [2/3] trading_strategies 테이블 생성 중...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trading_strategies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                strategy_name VARCHAR(100) NOT NULL COMMENT '전략명',
                description TEXT COMMENT '전략 설명',
                start_date DATE NOT NULL COMMENT '시작일',
                end_date DATE DEFAULT NULL COMMENT '종료일 (NULL = 진행 중)',
                initial_assets DECIMAL(15,2) COMMENT '시작 자산',
                target_assets DECIMAL(15,2) COMMENT '목표 금액',
                target_return_pct DECIMAL(8,2) COMMENT '목표 수익률 (%)',
                status ENUM('ACTIVE', 'COMPLETED', 'PAUSED') DEFAULT 'ACTIVE' COMMENT '상태',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='매매 전략 관리'
        """)
        print("   ✅ trading_strategies 테이블 생성 완료")

        # 3. asset_goals 테이블 생성 (목표 금액 관리)
        print("\n🎯 [3/3] asset_goals 테이블 생성 중...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS asset_goals (
                id INT AUTO_INCREMENT PRIMARY KEY,
                goal_name VARCHAR(100) NOT NULL COMMENT '목표명',
                target_amount DECIMAL(15,2) NOT NULL COMMENT '목표 금액',
                target_date DATE COMMENT '목표 달성일',
                is_active BOOLEAN DEFAULT TRUE COMMENT '활성 여부',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='자산 목표 관리'
        """)
        print("   ✅ asset_goals 테이블 생성 완료")

        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ 모든 마이그레이션이 성공적으로 완료되었습니다!")
        print("=" * 60)
        
        # 테이블 확인
        print("\n📋 생성된 테이블 확인:")
        for table in ['daily_assets', 'trading_strategies', 'asset_goals']:
            cursor.execute(f"DESCRIBE {table}")
            columns = cursor.fetchall()
            print(f"\n   [{table}] - {len(columns)} 컬럼")
            for col in columns[:5]:  # 처음 5개 컬럼만 표시
                print(f"      - {col['Field']}: {col['Type']}")
            if len(columns) > 5:
                print(f"      ... 외 {len(columns) - 5}개 컬럼")

    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_db()
