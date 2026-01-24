
from fastapi import APIRouter
from db import get_connection

router = APIRouter(prefix="/api/trading", tags=["trading"])

@router.get("/status")
def get_trading_status():
    """Get current open trades"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Fetch all OPEN trades
            cursor.execute("SELECT * FROM trade_history WHERE status='OPEN' ORDER BY entry_time DESC")
            open_trades = cursor.fetchall()
            return open_trades
    finally:
        conn.close()

@router.get("/history")
def get_trading_history(limit: int = 10):
    """Get closed trade history"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Fetch CLOSED trades
            cursor.execute("SELECT * FROM trade_history WHERE status='CLOSED' ORDER BY exit_time DESC LIMIT %s", (limit,))
            history = cursor.fetchall()
            return history
    finally:
        conn.close()
