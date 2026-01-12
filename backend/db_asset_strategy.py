
# ========================================
# Daily Assets (일별 자산) CRUD Functions
# ========================================
from db import get_connection
from datetime import datetime


def get_daily_assets(start_date=None, end_date=None, limit=365):
    """일별 자산 목록 조회"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM daily_assets WHERE 1=1"
            params = []
            
            if start_date:
                sql += " AND record_date >= %s"
                params.append(start_date)
            if end_date:
                sql += " AND record_date <= %s"
                params.append(end_date)
            
            sql += " ORDER BY record_date DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(sql, params)
            return cursor.fetchall()
    except Exception as e:
        print(f"Get Daily Assets Error: {e}")
        return []
    finally:
        conn.close()

def upsert_daily_asset(record_date, total_assets, daily_return_pct=None, daily_pnl=None, note=None):
    """일별 자산 등록/수정 (UPSERT) - 원화 기준"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 전일 자산 조회 (증감 계산용)
            cursor.execute("""
                SELECT total_assets FROM daily_assets 
                WHERE record_date < %s ORDER BY record_date DESC LIMIT 1
            """, (record_date,))
            prev = cursor.fetchone()
            
            daily_change = 0
            daily_change_pct = 0
            if prev and prev['total_assets']:
                prev_assets = float(prev['total_assets'])
                daily_change = float(total_assets) - prev_assets
                if prev_assets > 0:
                    daily_change_pct = (daily_change / prev_assets) * 100
            
            # 사용자 입력 수익률/손익이 있으면 사용
            if daily_return_pct is not None:
                daily_change_pct = daily_return_pct
            if daily_pnl is not None:
                daily_change = daily_pnl
            
            sql = """
                INSERT INTO daily_assets 
                (record_date, total_assets, daily_change, daily_change_pct, daily_return_pct, daily_pnl, note)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                total_assets = VALUES(total_assets),
                daily_change = VALUES(daily_change),
                daily_change_pct = VALUES(daily_change_pct),
                daily_return_pct = VALUES(daily_return_pct),
                daily_pnl = VALUES(daily_pnl),
                note = VALUES(note)
            """
            cursor.execute(sql, (record_date, total_assets, daily_change, daily_change_pct, daily_return_pct, daily_pnl, note))
        conn.commit()
        return True
    except Exception as e:
        print(f"Upsert Daily Asset Error: {e}")
        return False
    finally:
        conn.close()

def delete_daily_asset(record_date):
    """일별 자산 삭제"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM daily_assets WHERE record_date = %s", (record_date,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Delete Daily Asset Error: {e}")
        return False
    finally:
        conn.close()


def get_asset_summary():

    """자산 요약 통계"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            summary = {}
            
            # 최신 자산
            cursor.execute("SELECT * FROM daily_assets ORDER BY record_date DESC LIMIT 1")
            latest = cursor.fetchone()
            summary['latest'] = latest
            
            # 월간 변동 (당월 1일 기준)
            cursor.execute("""
                SELECT total_assets FROM daily_assets 
                WHERE record_date >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
                ORDER BY record_date ASC LIMIT 1
            """)
            month_start = cursor.fetchone()
            if latest and month_start:
                monthly_change = float(latest['total_assets']) - float(month_start['total_assets'])
                monthly_pct = (monthly_change / float(month_start['total_assets'])) * 100 if month_start['total_assets'] else 0
                summary['monthly_change'] = monthly_change
                summary['monthly_change_pct'] = monthly_pct
                summary['month_start_date'] = datetime.now().strftime('%Y-%m-01')
            else:
                summary['monthly_change'] = 0
                summary['monthly_change_pct'] = 0

            
            # 활성 목표
            cursor.execute("SELECT * FROM asset_goals WHERE is_active = TRUE ORDER BY id DESC LIMIT 1")
            summary['active_goal'] = cursor.fetchone()
            
            return summary
    except Exception as e:
        print(f"Get Asset Summary Error: {e}")
        return {}
    finally:
        conn.close()

# ========================================
# Asset Goals (목표 금액) CRUD Functions
# ========================================

def get_asset_goals():
    """목표 금액 목록 조회"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM asset_goals ORDER BY created_at DESC")
            return cursor.fetchall()
    except Exception as e:
        print(f"Get Asset Goals Error: {e}")
        return []
    finally:
        conn.close()

def create_asset_goal(goal_name, target_amount, target_date=None):
    """목표 금액 등록"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 기존 활성 목표 비활성화
            cursor.execute("UPDATE asset_goals SET is_active = FALSE WHERE is_active = TRUE")
            
            sql = "INSERT INTO asset_goals (goal_name, target_amount, target_date, is_active) VALUES (%s, %s, %s, TRUE)"
            cursor.execute(sql, (goal_name, target_amount, target_date))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Create Asset Goal Error: {e}")
        return None
    finally:
        conn.close()

def update_asset_goal(goal_id, data):
    """목표 금액 수정"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            fields = []
            params = []
            for field in ['goal_name', 'target_amount', 'target_date', 'is_active']:
                if field in data:
                    fields.append(f"{field} = %s")
                    params.append(data[field])
            
            if not fields:
                return False
            
            params.append(goal_id)
            sql = f"UPDATE asset_goals SET {', '.join(fields)} WHERE id = %s"
            cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Update Asset Goal Error: {e}")
        return False
    finally:
        conn.close()

def delete_asset_goal(goal_id):
    """목표 금액 삭제"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM asset_goals WHERE id = %s", (goal_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Delete Asset Goal Error: {e}")
        return False
    finally:
        conn.close()

# ========================================
# Trading Strategies (전략) CRUD Functions
# ========================================


def get_trading_strategies(status=None):
    """전략 목록 조회"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM trading_strategies WHERE 1=1"
            params = []
            
            if status:
                sql += " AND status = %s"
                params.append(status)
            
            sql += " ORDER BY created_at DESC"
            cursor.execute(sql, params)
            return cursor.fetchall()
    except Exception as e:
        print(f"Get Strategies Error: {e}")
        return []
    finally:
        conn.close()

def get_trading_strategy_by_id(strategy_id):
    """단일 전략 조회"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM trading_strategies WHERE id = %s", (strategy_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"Get Strategy Error: {e}")
        return None
    finally:
        conn.close()

def create_trading_strategy(data):
    """전략 등록"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO trading_strategies 
                (strategy_name, description, start_date, end_date, initial_assets, target_assets, target_return_pct, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                data.get('strategy_name'),
                data.get('description'),
                data.get('start_date'),
                data.get('end_date'),
                data.get('initial_assets'),
                data.get('target_assets'),
                data.get('target_return_pct'),
                data.get('status', 'ACTIVE')
            ))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Create Strategy Error: {e}")
        return None
    finally:
        conn.close()

def update_trading_strategy(strategy_id, data):
    """전략 수정"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            fields = []
            params = []
            allowed_fields = ['strategy_name', 'description', 'start_date', 'end_date', 
                            'initial_assets', 'target_assets', 'target_return_pct', 'status']
            
            for field in allowed_fields:
                if field in data:
                    fields.append(f"{field} = %s")
                    params.append(data[field])
            
            if not fields:
                return False
            
            params.append(strategy_id)
            sql = f"UPDATE trading_strategies SET {', '.join(fields)} WHERE id = %s"
            cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Update Strategy Error: {e}")
        return False
    finally:
        conn.close()

def delete_trading_strategy(strategy_id):
    """전략 삭제"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM trading_strategies WHERE id = %s", (strategy_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Delete Strategy Error: {e}")
        return False
    finally:
        conn.close()

def get_strategy_performance(strategy_id):
    """전략 성과 분석 - daily_assets 기반 계산"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 전략 정보 조회
            cursor.execute("SELECT * FROM trading_strategies WHERE id = %s", (strategy_id,))
            strategy = cursor.fetchone()
            if not strategy:
                return None
            
            start_date = strategy['start_date']
            end_date = strategy['end_date'] or datetime.now().strftime('%Y-%m-%d')
            initial_assets = float(strategy['initial_assets']) if strategy.get('initial_assets') else None
            
            # 시작 자산: 전략에 등록된 값 사용, 없으면 daily_assets에서 조회
            if not initial_assets:
                cursor.execute("""
                    SELECT total_assets FROM daily_assets 
                    WHERE record_date >= %s ORDER BY record_date ASC LIMIT 1
                """, (start_date,))
                start_row = cursor.fetchone()
                initial_assets = float(start_row['total_assets']) if start_row else None
            
            # 현재/종료 자산: daily_assets에서 최신 데이터
            cursor.execute("""
                SELECT total_assets, record_date FROM daily_assets 
                WHERE record_date <= %s ORDER BY record_date DESC LIMIT 1
            """, (end_date,))
            end_row = cursor.fetchone()
            current_assets = float(end_row['total_assets']) if end_row else None
            latest_date = str(end_row['record_date']) if end_row else None
            
            # 수익률 및 손익 계산
            total_pnl = 0
            total_return_pct = 0
            if initial_assets and current_assets:
                total_pnl = current_assets - initial_assets
                total_return_pct = (total_pnl / initial_assets) * 100
            
            # 기간 내 자산 기록 수 (매매 일수)
            cursor.execute("""
                SELECT COUNT(*) as count FROM daily_assets 
                WHERE record_date >= %s AND record_date <= %s
            """, (start_date, end_date))
            record_count = cursor.fetchone()['count'] or 0
            
            # 기간 내 수익/손실 일수
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN daily_change > 0 THEN 1 ELSE 0 END) as win_days,
                    SUM(CASE WHEN daily_change < 0 THEN 1 ELSE 0 END) as loss_days,
                    AVG(daily_change_pct) as avg_daily_pct
                FROM daily_assets 
                WHERE record_date >= %s AND record_date <= %s
            """, (start_date, end_date))
            daily_stats = cursor.fetchone()
            
            wins = int(daily_stats['win_days'] or 0)
            losses = int(daily_stats['loss_days'] or 0)
            total_days = wins + losses
            win_rate = (wins / total_days * 100) if total_days > 0 else 0
            avg_pnl_pct = float(daily_stats['avg_daily_pct'] or 0)
            
            return {
                'strategy': strategy,
                'total_trades': record_count,  # 기록된 자산 일수
                'wins': wins,  # 수익 일수
                'losses': losses,  # 손실 일수
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 0),
                'avg_pnl_pct': round(avg_pnl_pct, 2),
                'avg_hold_days': record_count,  # 기록 일수
                'total_return_pct': round(total_return_pct, 2),
                'start_assets': initial_assets,
                'end_assets': current_assets,
                'latest_date': latest_date
            }
    except Exception as e:
        print(f"Get Strategy Performance Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        conn.close()

