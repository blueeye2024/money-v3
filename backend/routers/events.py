from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from db import get_connection

router = APIRouter(prefix="/api/market-events", tags=["market-events"])

class EventModel(BaseModel):
    event_date: str
    event_time: Optional[str] = None
    title: str
    description: Optional[str] = ""
    importance: str = "MEDIUM"

@router.get("/")
def get_events(year: int, month: int):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Filter by YYYY-MM
            start_date = f"{year}-{month:02d}-01"
            if month == 12:
                end_date = f"{year+1}-01-01"
            else:
                end_date = f"{year}-{month+1:02d}-01"
            
            # Simple select, format in Python
            sql = """
                SELECT * FROM market_events 
                WHERE event_date >= %s AND event_date < %s 
                ORDER BY event_date ASC, event_time ASC
            """
            cursor.execute(sql, (start_date, end_date))
            rows = cursor.fetchall()
            
            # Convert timedelta to string HH:MM
            for r in rows:
                if r.get('event_time'):
                    # Check if it's timedelta
                    from datetime import timedelta
                    et = r['event_time']
                    if isinstance(et, timedelta):
                        total_seconds = int(et.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        r['event_time'] = f"{hours:02d}:{minutes:02d}"
                    else:
                         r['event_time'] = str(et)[:5] # Just in case it's string
            
            return rows
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR in get_events: {e}")
        raise e
    finally:
        conn.close()

@router.get("/today")
def get_today_events():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM market_events WHERE event_date = CURDATE() ORDER BY event_time ASC"
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            for r in rows:
                if r.get('event_time'):
                    from datetime import timedelta
                    et = r['event_time']
                    if isinstance(et, timedelta):
                        total_seconds = int(et.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        r['event_time'] = f"{hours:02d}:{minutes:02d}"
                    else:
                         r['event_time'] = str(et)[:5]

            return rows
    except Exception as e:
        print(f"ERROR in get_today_events: {e}")
        raise e
    finally:
        conn.close()

@router.post("/")
def create_event(event: EventModel):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # If empty string, treat as NULL
            e_time = event.event_time if event.event_time and event.event_time.strip() else None
            
            sql = """
            INSERT INTO market_events (event_date, event_time, title, description, importance)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (event.event_date, e_time, event.title, event.description, event.importance))
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        print(f"Event Create Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

class EventUpdateModel(BaseModel):
    event_time: Optional[str] = None
    title: str
    description: Optional[str] = ""
    importance: str = "MEDIUM"

@router.put("/{event_id}")
def update_event(event_id: int, event: EventUpdateModel):
    """[Ver 6.0.1] Update existing market event"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            e_time = event.event_time if event.event_time and event.event_time.strip() else None
            sql = """
            UPDATE market_events 
            SET event_time=%s, title=%s, description=%s, importance=%s
            WHERE id=%s
            """
            cursor.execute(sql, (e_time, event.title, event.description, event.importance, event_id))
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        print(f"Event Update Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.delete("/{event_id}")
def delete_event(event_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM market_events WHERE id=%s", (event_id,))
        conn.commit()
        return {"status": "success"}
    finally:
        conn.close()
