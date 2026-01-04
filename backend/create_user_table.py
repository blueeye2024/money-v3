import pymysql
import os

# DB 설정 (기존 설정 참고)
DB_HOST = "114.108.180.228"
DB_USER = "blueeye"
DB_PASSWORD = "blueeye0037!"
DB_NAME = "mywork_01"
DB_PORT = 3306

def create_users_table():
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            port=DB_PORT,
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = conn.cursor()
        
        # users 테이블 생성 SQL
        sql = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            name VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        
        cursor.execute(sql)
        conn.commit()
        print("✅ 'users' 테이블이 성공적으로 생성되었습니다 (또는 이미 존재함).")
        
    except Exception as e:
        print(f"❌ 테이블 생성 실패: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    create_users_table()
