from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from analysis import run_analysis, fetch_data, analyze_ticker, TARGET_TICKERS
from db import init_db, save_signal, check_last_signal, add_journal_entry, get_journal_entries
from sms import send_sms
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pandas as pd
import pytz
import uvicorn
from pydantic import BaseModel

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Initialize DB & Scheduler
@app.on_event("startup")
def on_startup():
    init_db()
    # Start Scheduler
    scheduler = BackgroundScheduler()
    # Interval set to 1 minute as requested
    scheduler.add_job(monitor_signals, 'interval', minutes=1)
    scheduler.start()

# 2. Monitor Logic (Runs every 1 min)
def monitor_signals():
    print(f"[{datetime.now()}] Monitoring Signals...")
    try:
        # Fetch fresh data
        data_30m, data_5m, _, _ = fetch_data()
        
        for ticker in TARGET_TICKERS:
            res = analyze_ticker(ticker, data_30m, data_5m)
            
            # Check for specific signals to alert
            # "진입" (Entry) or "돌파" (Breakout) are actionable
            if "진입" in res['position'] or "돌파" in res['position']:
                # Get last saved signal to avoid duplicates
                last_sig = check_last_signal(ticker)
                
                # Logic to determine if this is a NEW signal
                # We compare the 'signal_time_raw' (datetime obj)
                # Note: DB stores datetime.
                
                is_new = True
                current_raw_time = res.get('signal_time_raw')
                
                if current_raw_time is None: continue

                if last_sig:
                    # last_sig['signal_time'] is usually datetime from pymysql
                    # Ensure both are comparable (timezone aware vs naive)
                    # Often easier to compare string representation or timestamp
                    last_time = last_sig['signal_time']
                    
                    # Simple equality check
                    # Note: You might need to handle timezone alignment if DB converts to naive UTC
                    # But if we just save what we get, it should be comparable.
                    if last_time == current_raw_time:
                        is_new = False
                
                if is_new:
                    print(f"NEW SIGNAL DETECTED: {ticker} {res['position']}")
                    # Save to DB
                    save_signal({
                        'ticker': ticker,
                        'name': res['name'],
                        'signal_type': "BUY" if "매수" in res['position'] or "상단" in res['position'] else "SELL",
                        'position': res['position'],
                        'current_price': res['current_price'],
                        'signal_time_raw': current_raw_time,
                        'is_sent': True
                    })
                    
                    # Send SMS
                    # Format: [12/29 10:30] [SOXL] [매수 진입] [45.20] [RSI: 30.5]
                    send_sms(
                        stock_name=res['name'], 
                        signal_type=res['position'], 
                        price=res['current_price'], 
                        signal_time=res['signal_time'], # String format for SMS is fine
                        reason=f"RSI:{res['rsi']:.1f}"
                    )

    except Exception as e:
        print(f"Monitor Error: {e}")

@app.get("/api/report")
def get_report():
    try:
        data = run_analysis()
        return data
    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

# --- Journal APIs ---

@app.get("/api/journal")
def api_get_journal():
    entries = get_journal_entries()
    return entries

class JournalEntry(BaseModel):
    ticker: str
    stock_name: str = ""
    entry_date: str # ISO string
    entry_price: float
    quantity: int
    reason: str = ""
    exit_date: str = None
    exit_price: float = None

@app.post("/api/journal")
def api_add_journal(entry: JournalEntry):
    res = add_journal_entry(entry.dict())
    if res:
        return {"status": "success"}
    else:
        return {"status": "error"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
