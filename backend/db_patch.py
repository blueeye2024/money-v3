
# [Ver 6.6] Migration: Add group_name to managed_stocks
def migrate_v64_add_group_name_to_managed_stocks():
    """Add group_name column to managed_stocks if missing"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM managed_stocks LIKE 'group_name'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE managed_stocks ADD COLUMN group_name VARCHAR(50) DEFAULT '기타'")
                print("✅ Migration(v64): Added group_name column to managed_stocks")
    except Exception as e:
        print(f"Migration(v64) Error: {e}")
    finally:
        conn.close()

# [Ver 6.6] Update Holding Info (Meta Data)
def update_holding_info(ticker, category=None, group_name=None, is_holding=None):
    """Update metadata for a holding in managed_stocks"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check if record exists
            cursor.execute("SELECT ticker FROM managed_stocks WHERE ticker=%s", (ticker,))
            if not cursor.fetchone():
                # If missing, try to restore from Basic info (not ideal but better than error)
                # Or wait for transaction sync. 
                # For now, simplistic approach: Update if exists.
                return False, "Holding not found in managed list. Please add a transaction first."

            # Dynamic Update
            fields = []
            params = []
            
            if category is not None:
                fields.append("category = %s")
                params.append(category)
            if group_name is not None:
                fields.append("group_name = %s")
                params.append(group_name)
            if is_holding is not None:
                fields.append("is_holding = %s")
                params.append(is_holding) # Boolean or Int handling handled by driver usually
            
            if not fields:
                return True, "No changes"
            
            params.append(ticker)
            sql = f"UPDATE managed_stocks SET {', '.join(fields)} WHERE ticker = %s"
            cursor.execute(sql, params)
        conn.commit()
        return True, "Updated"
    except Exception as e:
        print(f"Update Holding Info Error: {e}")
        return False, str(e)
    finally:
        conn.close()
