
import sys
import os

# Add backend to path
sys.path.append('/home/blue/blue/my_project/money/backend')
from db import get_connection

def migrate_quantity_columns():
    print("Migrating DB Schema for Quantity Columns...")
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Add real_buy_qn to buy_stock
    try:
        cursor.execute("ALTER TABLE buy_stock ADD COLUMN real_buy_qn DECIMAL(10,2)")
        print("✅ Added real_buy_qn to buy_stock")
    except Exception as e:
        print(f"⚠️ buy_stock check: {e}")
        
    # 2. Add real_sell_qn to sell_stock
    try:
        cursor.execute("ALTER TABLE sell_stock ADD COLUMN real_sell_qn DECIMAL(10,2)")
        print("✅ Added real_sell_qn to sell_stock")
    except Exception as e:
        print(f"⚠️ sell_stock check: {e}")
        
    conn.commit()
    print("Migration Complete.")

if __name__ == "__main__":
    migrate_quantity_columns()
