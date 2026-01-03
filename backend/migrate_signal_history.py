#!/usr/bin/env python3
"""
DB Migration: Add signal_reason, time_kst, time_ny to signal_history table
"""
import sys
sys.path.append('/home/blue/blue/my_project/money/backend')

from db import get_connection

def migrate():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Add new columns
            migrations = [
                "ALTER TABLE signal_history ADD COLUMN IF NOT EXISTS signal_reason VARCHAR(100) AFTER signal_type",
                "ALTER TABLE signal_history ADD COLUMN IF NOT EXISTS time_kst VARCHAR(50) AFTER signal_time",
                "ALTER TABLE signal_history ADD COLUMN IF NOT EXISTS time_ny VARCHAR(50) AFTER time_kst"
            ]
            
            for migration_sql in migrations:
                try:
                    cursor.execute(migration_sql)
                    print(f"✅ Executed: {migration_sql[:60]}...")
                except Exception as e:
                    print(f"⚠️  Migration error (may already exist): {e}")
            
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
