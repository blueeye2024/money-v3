from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from typing import Optional, List
import datetime
import shutil
import os
import json
from db import get_connection

router = APIRouter(prefix="/api/daily-reports", tags=["daily-reports"])

UPLOAD_DIR = "../frontend/public/uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/")
def get_daily_reports(limit: int = 30):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM daily_reports ORDER BY report_date DESC LIMIT %s"
            cursor.execute(sql, (limit,))
            reports = cursor.fetchall()
            # Parse image_paths JSON if needed, though frontend handles stringified json usually.
            # But let's verify if we store as proper JSON string or List.
            for r in reports:
                if r['image_paths']:
                    try:
                        r['image_paths'] = json.loads(r['image_paths'])
                    except:
                        r['image_paths'] = []
            return reports
    finally:
        conn.close()

@router.get("/{date_str}")
def get_daily_report(date_str: str):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM daily_reports WHERE report_date = %s"
            cursor.execute(sql, (date_str,))
            report = cursor.fetchone()
            if report:
                if report['image_paths']:
                     try:
                        report['image_paths'] = json.loads(report['image_paths'])
                     except:
                         report['image_paths'] = []
                return report
            else:
                # Return empty template if not found? Or 404? 
                # Frontend expects a report object usually. Let's return null or 404.
                return None
    finally:
        conn.close()

@router.post("/")
def upsert_daily_report(
    report_date: str = Form(...),
    pre_market_strategy: str = Form(""),
    post_market_memo: str = Form(""),
    profit_rate: str = Form("0"),
    existing_images: str = Form("[]"), # JSON string of kept images
    new_images: List[UploadFile] = File(None)
):
    conn = get_connection()
    try:
        # 1. Handle Images
        # existing_images is a JSON string of paths -> list
        final_image_paths = []
        try:
            final_image_paths = json.loads(existing_images)
        except:
            pass

        if new_images:
            for file in new_images:
                if file.filename:
                    # Save file
                    safe_filename = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                    file_path = os.path.join(UPLOAD_DIR, safe_filename)
                    with open(file_path, "wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)
                    
                    # Store relative path for frontend
                    # Frontend serves 'uploads' from public? Yes if in public/uploads
                    final_image_paths.append(f"/uploads/{safe_filename}")

        # 2. Upsert DB
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO daily_reports (report_date, pre_market_strategy, post_market_memo, profit_rate, image_paths, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                pre_market_strategy = VALUES(pre_market_strategy),
                post_market_memo = VALUES(post_market_memo),
                profit_rate = VALUES(profit_rate),
                image_paths = VALUES(image_paths),
                updated_at = NOW()
            """
            cursor.execute(sql, (
                report_date, 
                pre_market_strategy, 
                post_market_memo, 
                float(profit_rate), 
                json.dumps(final_image_paths)
            ))
        conn.commit()
        return {"status": "success", "image_paths": final_image_paths}
    except Exception as e:
        print(f"Report Upsert Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.delete("/{date_str}")
def delete_daily_report(date_str: str):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # First get images to delete files?
            cursor.execute("SELECT image_paths FROM daily_reports WHERE report_date = %s", (date_str,))
            row = cursor.fetchone()
            if row and row['image_paths']:
                 # Optional: Delete actual files. 
                 # For now, skip to avoid deleting shared or wrong files safe side.
                 pass

            cursor.execute("DELETE FROM daily_reports WHERE report_date = %s", (date_str,))
        conn.commit()
        return {"status": "success"}
    finally:
        conn.close()
