
from apscheduler.schedulers.background import BackgroundScheduler
from populate_soxs import populate_soxs_data
import time

def run_maintenance_job():
    """
    Job to maintain exactly 3 days of SOXS data.
    Runs populate_soxs_data() which now handles TRUNCATE + Fetch 3 days logic.
    """
    print(f"⏰ [Maintenance] Starting SOXS 3-Day Window Maintenance Job at {time.strftime('%Y-%m-%d %H:%M:%S')}...")
    try:
        populate_soxs_data()
        print("✅ [Maintenance] SOXS Data Refreshed Successfully.")
    except Exception as e:
        print(f"❌ [Maintenance] Job Failed: {e}")

def start_maintenance_scheduler():
    scheduler = BackgroundScheduler()
    
    # Schedule to run periodically. 
    # Since we want to "Always maintain", running it every 5 minutes 
    # ensures that as "Today" progresses, new candles are added, 
    # and if day changes, old data is wiped by the logic in populate_soxs.
    
    # ACTUALLY: populate_soxs currently does TRUNCATE + INSERT.
    # So running it often is fine, it just refreshes the whole table.
    # Let's run it every 5 minutes to keep "Today's" data fresh and accurate.
    
    scheduler.add_job(run_maintenance_job, 'interval', minutes=5, id='soxs_maintenance')
    scheduler.start()
    print("🕒 SOXS Maintenance Scheduler Started (Every 5 mins)")
