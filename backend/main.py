from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from routers import reports, events, trading
from typing import Optional
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pandas as pd
import pytz
import uvicorn
from passlib.hash import pbkdf2_sha256
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "cheongan_fintech_secret_key_2026"
ALGORITHM = "HS256"

from analysis import run_analysis, fetch_data, TARGET_TICKERS, run_v2_signal_analysis
from sms import send_sms
from db import init_db, save_signal, check_last_signal, get_stocks, add_stock, delete_stock, add_transaction, get_transactions, update_transaction, delete_transaction, get_signals, save_sms_log, get_sms_logs, delete_all_signals, delete_sms_log, delete_all_sms_logs, get_ticker_settings, update_ticker_setting, update_stock_status, get_v2_buy_status, get_v2_sell_status, delete_holding

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Uploads
app.mount("/uploads", StaticFiles(directory="../frontend/public/uploads"), name="uploads")

# Include Routers
app.include_router(reports.router)
app.include_router(events.router)
app.include_router(trading.router)
from routers import crypto
app.include_router(crypto.router)
from routers import lab
app.include_router(lab.router)

# 1. Initialize DB & Scheduler
@app.on_event("startup")
def on_startup():
    from db import init_db, get_global_config, update_stock_prices, migrate_journal_transactions_v62, migrate_v63_add_is_holding, migrate_v64_add_group_name_to_managed_stocks, migrate_v67_add_new_columns_to_managed_stocks, migrate_v68_add_simulation_columns, migrate_add_change_pct_to_managed_stocks
    init_db()
    migrate_journal_transactions_v62()  # [Ver 6.2] Add new columns
    migrate_v63_add_is_holding()        # [Ver 6.3] Add is_holding column
    migrate_v64_add_group_name_to_managed_stocks() # [Ver 6.6] Add group_name
    migrate_v67_add_new_columns_to_managed_stocks() # [Ver 6.7] Add strategy columns
    migrate_v68_add_simulation_columns() # [Ver 6.8] Add simulation columns
    migrate_add_change_pct_to_managed_stocks() # [Ver 6.9] Add change_pct
    
    # Load SMS Setting from DB
    global SMS_ENABLED
    SMS_ENABLED = get_global_config("sms_enabled", True)
    print(f"Startup: SMS Enabled = {SMS_ENABLED}")

    # Start Scheduler (Singleton Lock)
    import fcntl
    import os
    
    lock_file = open("scheduler.lock", "w")
    try:
        # Try to lock. If fails, another worker has it.
        fcntl.lockf(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        
        print("🔒 Acquired Scheduler Lock. Starting Background Jobs...")
        scheduler = BackgroundScheduler()
        # [Updated] Analysis/Signal Check: Every 1 minute (60s) for faster feedback
        scheduler.add_job(monitor_signals, 'interval', seconds=60)
        
        # [New] Auto Price Update (Every 10 secs)
        def update_prices_job():
            try:
                # Only run during market hours + buffer (roughly) or freely if quota allows.
                # For now, run unconditionally as requested.
                update_stock_prices()
            except Exception as e:
                print(f"Auto Price Update Failed: {e}")

        scheduler.add_job(update_prices_job, 'interval', seconds=10)
        
        # [New] Cheongan V2 Signal Analysis (Every 10 secs)
        scheduler.add_job(run_v2_signal_analysis, 'interval', seconds=10)
        
        # [New] SOXS Data Maintenance Scheduler (User Request: 3 Days Rolling)
        from scheduler_soxs import start_maintenance_scheduler as start_soxs_sched
        start_soxs_sched()

        # [Ver 5.3.1] Pre-emptive Token Refresh (Every 10 mins)
        # Prevent Rate Limit Loops by refreshing token 30 mins before expiry
        def token_maintenance_job():
            from kis_api_v2 import kis_client
            try:
                 kis_client.ensure_fresh_token(buffer_minutes=30)
            except Exception as e:
                 print(f"Token Maintenance Error: {e}")
                 
        scheduler.add_job(token_maintenance_job, 'interval', minutes=10)

        # [Reliability] Heartbeat Logging (Every 1 hour)
        def heartbeat_job():
            print(f"❤️ System Heartbeat: {datetime.now()} - Scheduler is alive.")
        scheduler.add_job(heartbeat_job, 'interval', hours=1)

        scheduler.start()
        print("✅ Scheduler Started: Monitor(1m), PriceUpdate(5m), Token(10m)")
        
    except IOError:
        print("⚠️ Scheduler Lock Failed (Already running in another worker). Skipping Scheduler.")



# ... (API endpoints)

@app.post("/api/system/backfill")
def api_trigger_backfill():
    """Manually trigger deep data fetch (30 days)"""
    try:
        # Run in background to avoid timeout
        import threading
        t = threading.Thread(target=data_backfill_job)
        t.start()
        return {"status": "success", "message": "데이터 동기화(최근 30일) 작업이 백그라운드에서 시작되었습니다."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Global SMS Control (Now persistent via DB)
SMS_ENABLED = True
SMS_THROTTLE_MINUTES = 30

class SMSSettingModel(BaseModel):
    enabled: bool

class TickerSettingUpdate(BaseModel):
    ticker: str
    is_visible: bool

class CapitalModel(BaseModel):
    amount: float = 0

class HoldingUpdateModel(BaseModel):
    ticker: str
    qty: Optional[int] = None
    avg_price: Optional[float] = None
    current_price: Optional[float] = None
    group_name: Optional[str] = None
    category: Optional[str] = None
    is_holding: Optional[bool] = None
    target_sell_price: Optional[float] = None
    expected_sell_date: Optional[str] = None # Expecting 'YYYY-MM-DD'
    strategy_memo: Optional[str] = None
    manual_qty: Optional[int] = None
    manual_price: Optional[float] = None
    quantity: Optional[int] = None
    price: Optional[float] = None

@app.put("/api/holdings/{ticker}")
def update_holding_endpoint(ticker: str, data: HoldingUpdateModel):
    from db import update_holding_info
    
    success, msg = update_holding_info(
        ticker, 
        category=data.category, 
        group_name=data.group_name, 
        is_holding=data.is_holding,
        target_sell_price=data.target_sell_price,
        expected_sell_date=data.expected_sell_date,
        strategy_memo=data.strategy_memo,
        manual_qty=data.manual_qty,
        manual_price=data.manual_price,
        quantity=data.quantity,
        price=data.price or data.avg_price # Valid mappings
    )
    
    if success:
        return {"status": "success", "message": "Updated"}
    else:
        return {"status": "error", "message": msg}


@app.get("/api/settings/sms")
def get_sms_setting():
    from db import get_global_config
    enabled = get_global_config("sms_enabled", True)
    global SMS_ENABLED
    SMS_ENABLED = enabled
    return {"enabled": SMS_ENABLED}

@app.post("/api/settings/sms")
def set_sms_setting(setting: SMSSettingModel):
    from db import set_global_config
    global SMS_ENABLED
    SMS_ENABLED = setting.enabled
    set_global_config("sms_enabled", SMS_ENABLED)
    print(f"SMS System Enabled (Saved to DB): {SMS_ENABLED}")
    return {"status": "success", "enabled": SMS_ENABLED}
    return {"status": "success", "enabled": SMS_ENABLED}

@app.get("/api/capital")
def get_capital_api():
    try:
        from db import get_total_capital
        return get_total_capital()
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/capital")
def set_capital_api(data: CapitalModel):
    try:
        from db import set_total_capital
        if set_total_capital(data.amount):
            return {"status": "success", "amount": data.amount}
        return {"status": "error"}
    except Exception as e:
        return {"error": str(e)}

class StrategyMemoModel(BaseModel):
    memo: str

@app.get("/api/strategy_memo")
def get_strategy_memo_api():
    try:
        from db import get_strategy_memo
        return {"memo": get_strategy_memo()}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/strategy_memo")
def set_strategy_memo_api(data: StrategyMemoModel):
    try:
        from db import set_strategy_memo
        if set_strategy_memo(data.memo):
            return {"status": "success"}
        return {"status": "error"}
    except Exception as e:
        return {"error": str(e)}


# 2. Monitor Logic (Runs every 1 min)
def update_prices_job():
    """5분마다 종목 현재가 업데이트"""
    from db import update_stock_prices
    try:
        print(f"[{datetime.now()}] 종목 현재가 업데이트 시작...")
        update_stock_prices()
    except Exception as e:
        print(f"현재가 업데이트 작업 오류: {e}")

    try:
        # [MODIFIED] Periodic Deep Fetch (Backfill)
        # Every hour, ensure we have full month history in DB to prevent gaps
        if datetime.now().minute == 0:
             print("🕒 Hourly Deep Fetch Triggered (Backfill Data)")
             from analysis import fetch_data
             fetch_data(force=True)
             # pass was previously here doing nothing useful
    except Exception as e:
        print(f"Hourly Backfill Error: {e}")

def data_backfill_job():
    """주기적으로 과거 데이터(1개월)를 다시 가져와 DB 구멍을 메꾸는 작업"""
    try:
        print(f"[{datetime.now()}] 🔄 Data Backfill Job Started (1mo deep fetch)...")
        from analysis import fetch_data
        # Force fetch, but fetch_data determines period. 
        # We need to ideally pass a param? For now, fetch_data logic uses "1mo" if empty.
        # But if not empty, it uses "5d". We want "1mo" periodically.
        # Let's modify fetch_data to accept 'period' arg or just trigger simple fetch.
        
        # Temporary: Just call fetch_data(force=True) relies on '5d'.
        # To truly backfill, we should call yfinance directly here or enhance fetch_data.
        # Let's enhance fetch_data to take a period argument in next step.
        fetch_data(force=True, override_period="1mo") 
        print("✅ Backfill Job Completed.")
    except Exception as e:
         print(f"Backfill Job Error: {e}")

def process_system_trading(ticker, result):
    """
    Check analysis result and log virtual system trades.
    Only for SOXL, SOXS as requested.
    """
    if ticker not in ["SOXL", "SOXS"]: return
    
    try:
        from db import get_last_system_trade, log_system_trade
        
        # 1. Get Current Analysis State
        # 'final' is True if all 3 filters are MET. This is our entry signal.
        is_buy_signal = result.get('final') 
        
        # Determine Sell Signal (Dead Cross or Stop Loss)
        # analysis.py sets 'is_sell_signal' based on tech analysis (Dead Cross etc)
        is_sell_signal = result.get('is_sell_signal', False)
        
        # 2. Get Last Trade State
        last_trade = get_last_system_trade(ticker)
        # Default to 'SELL' (Closed) if no history
        last_type = last_trade['trade_type'] if last_trade else 'SELL' 
        
        current_price = result.get('current_price', 0)
        if current_price <= 0: return # Invalid price
        
        # A. Buy Entry
        # Condition: Signal is BUY AND We are currently NOT holding (Last was SELL)
        if is_buy_signal and last_type != 'BUY':
             print(f"🤖 SYSTEM TRADE: {ticker} BUY SIGNAL detected at {current_price}")
             log_system_trade({
                 'ticker': ticker,
                 'trade_type': 'BUY',
                 'price': current_price,
                 'trade_time': datetime.now(),
                 'strategy_note': 'Cheongan Triple Filter Met'
             })
             
        # B. Sell Exit
        # Condition: Signal is SELL AND We are currently HOLDING (Last was BUY)
        elif is_sell_signal and last_type == 'BUY':
             print(f"🤖 SYSTEM TRADE: {ticker} SELL SIGNAL detected at {current_price}")
             log_system_trade({
                 'ticker': ticker,
                 'trade_type': 'SELL',
                 'price': current_price,
                 'trade_time': datetime.now(),
                 'strategy_note': 'Dead Cross / Stop Loss'
             })
             
    except Exception as e:
        print(f"System Trading Logic Error ({ticker}): {e}")


# [Ver 5.7.3] Global Sound Queue
PENDING_SOUNDS = []
SOUND_SENT_LOG = {} # {code: signal_dt_obj}

def monitor_signals():
    global SMS_ENABLED
    global SOUND_SENT_LOG
    print(f"[{datetime.now()}] Monitoring Signals... SMS Enabled: {SMS_ENABLED}")
    
    try:
        # [NEW] Refresh Market Indices (S&P500, etc) to DB First
        from analysis import refresh_market_indices
        refresh_market_indices()

        # Use run_analysis for all processing to ensure consistency with dashboard
        # Force update cache in background job so frontend gets fast cached data
        full_report = run_analysis(force_update=True)
        stocks_data = full_report.get('stocks', [])

        # [User Request] Lab Data Auto Save (Every 5 mins)
        # 10s polling -> Trigger at :00, :05, ... (+- buffer?) 
        # Since this runs every 60s, checking 'minute % 5 == 0' works ONLY IF it aligns.
        # But scheduler runs at :00 seconds? No, depends on start time.
        # However, checking current minute % 5 == 0 is the standard way. 
        # To avoid multiple triggers in same minute (if loop takes long?), we trust 60s interval.
        now_dt = datetime.now()
        if now_dt.minute % 5 == 0:
            print(f"🧪 [Lab Data] 5m Auto-Save Triggered (Time: {now_dt.strftime('%H:%M:%S')})")
            try:
                from db_lab import save_realtime_lab_data
                import pytz
                
                # Calc US Time
                utc = pytz.utc
                eastern = pytz.timezone('US/Eastern')
                now_utc = datetime.now(utc)
                now_est = now_utc.astimezone(eastern)
                candle_time_us = now_est.replace(second=0, microsecond=0)
                
                lab_save_list = []
                for s in stocks_data:
                    if 'score' not in s: continue
                    
                    details = s.get('cheongan_details', {})
                    breakdown = s.get('score_breakdown', {})
                    
                    # [Ver 7.6.1] Fixed Key Mapping (from analysis.py breakdown)
                    s_energy = breakdown.get('energy', 0)
                    s_atr = breakdown.get('atr', 0)
                    s_bbi = breakdown.get('bbi', 0)
                    s_rsi = breakdown.get('rsi', 0)
                    s_macd = breakdown.get('macd', 0)
                    s_vol = breakdown.get('vol', 0) 
                    s_slope = breakdown.get('slope', 0) # [Ver 9.2.0] New

                    lab_save_list.append({
                        'ticker': s.get('ticker'),
                        'candle_time': candle_time_us,
                        'open': 0, 'high': 0, 'low': 0, 
                        'close': s.get('current_price', 0),
                        'volume': 0,
                        'ma10': s.get('ma10', 0),
                        'ma30': s.get('ma30', 0),
                        'change_pct': s.get('change_pct', 0) or s.get('daily_change', 0),
                        'scores': {
                            'total': s.get('score', 0),
                            'sig1': details.get('sig1', 0),
                            'sig2': details.get('sig2', 0),
                            'sig3': details.get('sig3', 0),
                            'energy': s_energy,
                            'atr': s_atr,
                            'bbi': s_bbi,
                            'rsi': s_rsi,
                            'macd': s_macd,
                            'vol': s_vol,
                            'slope': s_slope
                        }
                    })
                
                if lab_save_list:
                    save_realtime_lab_data(lab_save_list)
                    
            except Exception as e:
                print(f"❌ Lab Auto-Save Failed: {e}")

        
        for stock_res in stocks_data:
            ticker = stock_res['ticker']
            res = stock_res # Use the result from run_analysis
            
            # [NEW] System Auto-Trading Log (Virtual Portfolio)
            process_system_trading(ticker, res)
            
            # Skip if analysis failed
            if 'error' in res or 'position' not in res:
                print(f"Skipping {ticker} due to analysis error: {res.get('error', 'No position data')}")
                continue

            # Check for specific signals to alert (User Request: Score >= 70 OR Entry/Breakout)
            score = res.get('score', 0)
            is_entry_or_breakout = "진입" in res['position'] or "돌파" in res['position']
            is_high_score_signal = ("매수" in res['position'] or "매도" in res['position']) and score >= 70
            
            if is_entry_or_breakout or is_high_score_signal:
                # Get last saved signal to avoid duplicates
                last_sig = check_last_signal(ticker)
                
                is_new = True
                current_raw_time = res.get('signal_time_raw')
                
                if current_raw_time is None: continue

                if last_sig:
                    last_time = last_sig['signal_time']
                    # Check 30-min duplicate window (User Request)
                    try:
                        # Convert to pandas datetime for easy diff
                        lt = pd.to_datetime(last_time)
                        ct = pd.to_datetime(current_raw_time)
                        
                        # Calculate diff in minutes
                        diff_mins = (ct - lt).total_seconds() / 60.0
                        
                        # If same signal type AND within 30 mins, ignore
                        # (Assume position text equality implies same signal type)
                        if diff_mins < 10 and last_sig['position'] == res['position']:
                            print(f"Skipping duplicate signal for {ticker} (Last: {lt}, Curr: {ct}, Diff: {diff_mins:.1f}m)")
                            is_new = False
                        
                        # Also keep strict timestamp check just in case
                        if str(last_time) == str(current_raw_time):
                            is_new = False
                            
                    except Exception as e:
                        print(f"Date compare error for {ticker}: {e}")
                        if str(last_time) == str(current_raw_time):
                            is_new = False
                
                # 7-day de-duplication for standard signal saving
                if is_new: # Only check if not already marked as duplicate by 30-min window
                    try:
                        from db import get_connection
                        with get_connection() as conn:
                            with conn.cursor() as cursor:
                                cursor.execute("""
                                    SELECT id FROM signal_history 
                                    WHERE ticker=%s AND position_desc=%s 
                                    AND created_at >= NOW() - INTERVAL 7 DAY
                                    LIMIT 1
                                """, (ticker, res['position']))
                                if cursor.fetchone():
                                    print(f"Skipping 7-day duplicate signal for {ticker} ({res['position']})")
                                    is_new = False
                    except Exception as e:
                        print(f"Signal de-duplication error {ticker}: {e}")
                
                if is_new:
                    print(f"NEW SIGNAL DETECTED: {ticker} {res['position']}")
                    
                    # 1. Send SMS (if enabled and not throttled)
                    is_sent = False
                    if SMS_ENABLED:
                        from db import check_recent_sms_log
                        
                        # Throttle Check
                        # Check if we sent a similar message for this stock recently
                        recent = check_recent_sms_log(res['name'], res['position'], SMS_THROTTLE_MINUTES)
                        
                        if recent:
                            print(f"SMS Throttled for {ticker}: Already sent in last {SMS_THROTTLE_MINUTES} mins.")
                        else:
                            # Send
                            # User Request: Ticker, Type(Buy/Sell), Price, Score
                            short_pos = "매수" if "매수" in res['position'] or "상단" in res['position'] else "매도"
                            score = res.get('score', 0)
                            sms_reason = f"{score}점"
                            
                            from analysis import get_current_time_str_sms
                            time_str = get_current_time_str_sms()
                            
                            success = send_sms(
                                stock_name=ticker, # Use Ticker instead of Name
                                signal_type=short_pos, 
                                price=res['current_price'], 
                                signal_time=time_str,
                                reason=sms_reason
                            )
                            if success:
                                is_sent = True
                                msg = f"[{ticker}] [{short_pos}] [${res['current_price']}] [{sms_reason}]"
                                save_sms_log(receiver="01044900528", message=msg, status="Success")

                    save_signal({
                        'ticker': ticker,
                        'name': res['name'],
                        'signal_type': "BUY" if "매수" in res['position'] or "상단" in res['position'] else "SELL",
                        'position': res['position'],
                        'current_price': res['current_price'],
                        'signal_time_raw': current_raw_time.strftime('%Y-%m-%d %H:%M:%S') if isinstance(current_raw_time, datetime) else str(current_raw_time).split('.')[0].replace('T', ' '),
                        'is_sent': is_sent,
                        'score': res.get('score', 0),
                        'interpretation': res.get('score_interpretation', '')
                    })

        # --- Cheongan Master Signal Monitoring ---
        regime_data = full_report.get('market_regime', {}).get('details', {})
        if regime_data:
            for k_ticker in ['SOXL', 'SOXS']:
                m_res = regime_data.get(k_ticker.lower(), {})
                if not m_res: continue
                
                # A. Final Signal Met
                if m_res.get('final'):
                    from db import check_recent_sms_log
                    m_pos = f"마스터 {k_ticker} 진입"
                    # User: 30 min throttle
                    recent = check_recent_sms_log(k_ticker, m_pos, 30)
                    
                    if not recent and SMS_ENABLED:
                        send_sms(
                            stock_name=k_ticker,
                            signal_type="마스터 진입",
                            price=full_report['holdings'].get(k_ticker, {}).get('current_price', 0),
                            signal_time=datetime.now().strftime("%m-%d %H:%M"),
                            reason="트리플 필터 만족"
                        )
                        save_sms_log(receiver="01044900528", message=f"[{k_ticker}] [{m_pos}] 완성", status="Success")

                # B. 5m Dead Cross Warning (Warning 5m)
                if m_res.get('step3'):
                    from db import check_recent_sms_log
                    m_pos = f"마스터 {k_ticker} Step3"
                    recent = check_recent_sms_log(k_ticker, m_pos, 30)
                    if not recent and SMS_ENABLED:
                        send_sms(k_ticker, f"Step3 ({k_ticker})", full_report['holdings'].get(k_ticker, {}).get('current_price', 0), "Step3 진입")

                # B. 5m Dead Cross Warning (Warning 5m)
                if m_res.get('warning_5m'):
                    from db import check_recent_sms_log
                    w_pos = f"{k_ticker} 5분봉 경고"
                    recent = check_recent_sms_log(k_ticker, w_pos, 30)
                    
                    if not recent and SMS_ENABLED:
                        send_sms(
                            stock_name=k_ticker,
                            signal_type="5분봉 경고",
                            price=full_report['holdings'].get(k_ticker, {}).get('current_price', 0),
                            signal_time=datetime.now().strftime("%m-%d %H:%M"),
                            reason="데드크로스 발생"
                        )
                        save_sms_log(receiver="01044900528", message=f"[{k_ticker}] [{w_pos}] 발생", status="Success")

                # C. Trend Break (Sell Signal)
                if m_res.get('is_sell_signal'):
                    from db import check_recent_sms_log
                    s_pos = f"{k_ticker} 추세 붕괴(SELL)"
                    recent_s = check_recent_sms_log(k_ticker, s_pos, 30)
                    
                    if not recent_s and SMS_ENABLED:
                        send_sms(
                            stock_name=k_ticker,
                            signal_type="매도(EXIT)",
                            price=full_report['holdings'].get(k_ticker, {}).get('current_price', 0),
                            signal_time="현재",
                            reason="30분봉 추세 이탈"
                        )
                        save_sms_log(receiver="01044900528", message=f"[{k_ticker}] [{s_pos}] 발생", status="Success")

        # [Ver 5.7.3] Sound Matching Logic (User Request)
        # SOXL (BULL TOWER) -> ULB1/2/3, ULS1/2/3
        # SOXS (BEAR TOWER) -> USB1/2/3, USS1/2/3
        try:
            current_time = datetime.now()
            
            for stock_res in stocks_data:
                t = stock_res.get('ticker')
                if t not in ['SOXL', 'SOXS']: continue
                
                # Check V2 Buy Status
                v2_buy = stock_res.get('v2_buy') # injected in determine_market_regime_v2
                if v2_buy:
                    # SOXL: LB, SOXS: SB (System Auto)
                    prefix = "LB" if t == 'SOXL' else "SB"
                    
                    # Helper to enqueue sound
                    def try_enqueue_sound(suffix, dt_str, code_prefix):
                        if dt_str:
                            dt = datetime.strptime(str(dt_str), '%Y-%m-%d %H:%M:%S')
                            if (current_time - dt).total_seconds() < 60: # Recent trigger (< 1 min)
                                code = f"{code_prefix}{suffix}"
                                # Check if already sent for this specific timestamp
                                last_sent_dt = SOUND_SENT_LOG.get(code)
                                if str(last_sent_dt) != str(dt):
                                    # [Ver 6.5.7] V2 Algo Sounds 재활성화
                                    if code not in PENDING_SOUNDS: PENDING_SOUNDS.append(code)
                                    SOUND_SENT_LOG[code] = dt
                                    print(f"🔊 V2 Algo Sound Queued: {code} (Signal: {dt})")

                    # Check Steps
                    if v2_buy.get('buy_sig1_yn') == 'Y': try_enqueue_sound("1", v2_buy.get('buy_sig1_dt'), prefix)
                    if v2_buy.get('buy_sig2_yn') == 'Y': try_enqueue_sound("2", v2_buy.get('buy_sig2_dt'), prefix)
                    if v2_buy.get('buy_sig3_yn') == 'Y': try_enqueue_sound("3", v2_buy.get('buy_sig3_dt'), prefix)

                # Check V2 Sell Status
                v2_sell = stock_res.get('v2_sell')
                if v2_sell:
                    # SOXL: LS, SOXS: SS (System Auto)
                    prefix = "LS" if t == 'SOXL' else "SS"
                    
                    def try_enqueue_sound_sell(suffix, dt_str, code_prefix):
                        if dt_str:
                            dt = datetime.strptime(str(dt_str), '%Y-%m-%d %H:%M:%S')
                            if (current_time - dt).total_seconds() < 60:
                                code = f"{code_prefix}{suffix}"
                                last_sent_dt = SOUND_SENT_LOG.get(code)
                                if str(last_sent_dt) != str(dt):
                                    # [Ver 6.5.7] V2 Algo Sounds 재활성화
                                    if code not in PENDING_SOUNDS: PENDING_SOUNDS.append(code)
                                    SOUND_SENT_LOG[code] = dt
                                    print(f"🔊 V2 Algo Sound Queued: {code} (Signal: {dt})")

                    if v2_sell.get('sell_sig1_yn') == 'Y': try_enqueue_sound_sell("1", v2_sell.get('sell_sig1_dt'), prefix)
                    if v2_sell.get('sell_sig2_yn') == 'Y': try_enqueue_sound_sell("2", v2_sell.get('sell_sig2_dt'), prefix)
                    if v2_sell.get('sell_sig3_yn') == 'Y': try_enqueue_sound_sell("3", v2_sell.get('sell_sig3_dt'), prefix)

                # [Ver 5.7.5] Check Price Level Alerts Logic (Prioritize Highest Stage)
                try:
                    from db import get_price_levels
                    active_levels = get_price_levels(t)
                    now_db = datetime.now()
                    
                    # Collect triggers
                    recent_buy_triggers = []
                    recent_sell_triggers = []
                    
                    for lvl in active_levels:
                        # [FIX] Check Active Status
                        if lvl.get('is_active') != 'Y': continue

                        if lvl['triggered'] == 'Y' and lvl.get('triggered_at'):
                            # Calculate age of trigger
                            trig_dt = lvl['triggered_at']
                            if isinstance(trig_dt, str):
                                trig_dt = datetime.strptime(trig_dt, '%Y-%m-%d %H:%M:%S')
                            
                            age_secs = (now_db - trig_dt).total_seconds()
                            if age_secs < 60: # Recently triggered
                                if lvl['level_type'] == 'BUY':
                                    recent_buy_triggers.append(lvl['stage'])
                                elif lvl['level_type'] == 'SELL':
                                    recent_sell_triggers.append(lvl['stage'])

                    # [Ver 5.8] Use Distinct Sounds for Manual Alerts (LB/LS/SB/SS)
                    # SOXL -> L, SOXS -> S
                    # Buy -> B, Sell -> S
                    # User Manual -> Prefix 'U' (ULB1, USB2...)
                    ticker_code = "L" if t == 'SOXL' else "S"
                    
                    if recent_buy_triggers:
                        max_stage = max(recent_buy_triggers)
                        sound_code = f"U{ticker_code}B{max_stage}"
                        
                        last_sent = SOUND_SENT_LOG.get(sound_code)
                        # Throttle check
                        if str(last_sent) != str(trig_dt):
                             if sound_code not in PENDING_SOUNDS:
                                 PENDING_SOUNDS.append(sound_code)
                                 print(f"🔊 Queued Manual Alert Sound: {sound_code} (Stage {max_stage})")
                                 SOUND_SENT_LOG[sound_code] = trig_dt # Log usage
                    
                    if recent_sell_triggers:
                        max_stage = max(recent_sell_triggers)
                        sound_code = f"U{ticker_code}S{max_stage}"
                        
                        last_sent = SOUND_SENT_LOG.get(sound_code)
                        if str(last_sent) != str(trig_dt):
                            if sound_code not in PENDING_SOUNDS:
                                PENDING_SOUNDS.append(sound_code)
                                print(f"🔊 Queued Manual Alert Sound: {sound_code} (Stage {max_stage})")
                                SOUND_SENT_LOG[sound_code] = trig_dt

                except Exception as e:
                    print(f"Price Alert Sound Check Error {t}: {e}")
                                
        except Exception as e:
            print(f"Sound Logic Error: {e}")

    except Exception as e:
        print(f"Monitor Signals Error: {e}")



@app.get("/api/report")
def get_report():
    try:
        from db import get_current_holdings, get_ticker_settings, get_managed_stock_price
        from analysis import get_cached_report
        
        # 1. Get Cached Analysis (Updates every 5 mins)
        data = get_cached_report()
        
        # If cache is empty (startup), run once
        if not data:
             print("⚠️ Cache empty, triggering first analysis...")
             from analysis import run_analysis
             data = run_analysis(force_update=True)

        if not data:
             return {"error": "Analysis data not ready"}

        # 2. Inject Real-time Price (Updates every 10 secs via DB Job)
        # We create a shallow copy to avoid mutating the cached object deeply if not needed, 
        # but actually we want to return a fresh response.
        # Let's clone the list of stocks to modify prices.
        
        response_data = data.copy()
        response_data['stocks'] = [] # Re-build stocks list with fresh prices
        
        cached_stocks = data.get('stocks', [])
        settings = get_ticker_settings()
        
        for stock_cache in cached_stocks:
            # Create a copy of the stock dict
            stock = stock_cache.copy()
            ticker = stock['ticker']
            
            # Fetch Real-time Price from DB (which is updated every 10s by KIS)
            # We use get_managed_stock_price or similar. 
            # Actually db.py has get_stock(ticker) or we can look up from get_stocks().
            # Let's import a helper or query directly.
            # Assuming 'get_managed_stock_price' or similar exists or we use 'get_stocks'.
            # get_stocks() returns detailed info.
            
            # Let's assume we can get the latest price easily. 
            # For efficiency, maybe get all stocks at once?
            # But get_report is polled every 10s.
            
            # Let's use `get_stock` from db.py if available, or just trust the scheduler updated DB and we read it.
            # Ideally we read from the same source `update_prices_job` writes to.
            # `update_prices_job` updates `managed_stocks` table.
            # let's add `get_realtime_price(ticker)` to db.py or use existing.
            # For now, to minimize `db.py` changes, I'll rely on `get_stocks()` or `get_stock_price(ticker)`.
            # I will trust `stock['current_price']` in the CACHE is 5 mins old.
            # I need to overwrite it.
            
            # Quick DB lookup for price
            rt_price_info = get_managed_stock_price(ticker) # Need to verify this exists or create it
            if rt_price_info:
                 stock['current_price'] = rt_price_info['price']
                 stock['daily_change'] = rt_price_info['change'] # This comes from KIS 'rate'
                 
                 # Recalculate 'profit_rate' if holding?
                 # if stock['position'] == 'HOLD' etc...
                 # The 'profit_rate' in analysis is based on old price.
                 # If we update price, we should probably update profit display too.
                 # For simplicity, we update Price and Rate (most important).
            
            stock['is_visible'] = settings.get(ticker, True)
            response_data['stocks'].append(stock)
            

        # 3. Inject Pending Sounds (One-time consume)
        global PENDING_SOUNDS
        if PENDING_SOUNDS:
            response_data['sounds'] = list(set(PENDING_SOUNDS)) # Remove duplicates
            PENDING_SOUNDS = [] # Clear queue
            print(f"🔊 Sent Sounds: {response_data['sounds']}")
        else:
            response_data['sounds'] = []

        return response_data
    except Exception as e:
        print(f"Get Report Error: {e}")
        return {"error": str(e)}

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/signals")
def api_get_signals(ticker: str = None, start_date: str = None, end_date: str = None, limit: int = 30):
    return get_signals(ticker, start_date, end_date, limit)

@app.delete("/api/signals/all")
def api_delete_all_signals():
    if delete_all_signals():
        return {"status": "success"}
    return {"status": "error"}

@app.delete("/api/signals/{id}")
def api_delete_signal(id: int):
    # Import delete_signal from db
    from db import delete_signal
    if delete_signal(id):
        return {"status": "success"}
    return {"status": "error"}

@app.get("/api/managed-stocks")
def get_managed_stocks_api():
    try:
        from db import get_managed_stocks
        stocks = get_managed_stocks()
        return stocks
    except Exception as e:
        print(f"Error fetching managed stocks: {e}")
        return []

@app.post("/api/managed-stocks")
def add_managed_stock_api(data: dict):
    from db import add_managed_stock
    if add_managed_stock(data):
        return {"status": "success"}
    return {"status": "error"}

@app.put("/api/managed-stocks/{id}")
def update_managed_stock_api(id: int, data: dict):
    from db import update_managed_stock
    if update_managed_stock(id, data):
        return {"status": "success"}
    return {"status": "error"}

@app.put("/api/managed-stocks/{id}/manual-price")
def update_manual_price_api(id: int, data: dict):
    """수동으로 현재가 입력 (자동 업데이트 제외)"""
    from db import update_manual_price
    price = data.get('price')
    if price is not None and update_manual_price(id, price):
        return {"status": "success"}
    return {"status": "error", "message": "가격 정보가 필요합니다"}

@app.delete("/api/managed-stocks/{id}")
def delete_managed_stock_api(id: int):
    from db import delete_managed_stock
    if delete_managed_stock(id):
        return {"status": "success"}
    return {"status": "error"}


@app.get("/api/dashboard-settings")
def api_get_dashboard_settings():
    return get_ticker_settings()

@app.post("/api/dashboard-settings")
def api_update_dashboard_setting(setting: TickerSettingUpdate):
    if update_ticker_setting(setting.ticker, setting.is_visible):
        return {"status": "success"}
    return {"status": "error"}

@app.get("/api/exchange-rate")
def api_get_exchange_rate():
    from analysis import MARKET_INDICATORS
    import yfinance as yf
    try:
        t = yf.Ticker(MARKET_INDICATORS["KRW"])
        hist = t.history(period="1d")
        if not hist.empty:
            return {"rate": float(hist['Close'].iloc[-1])}
        return {"rate": 1350.0}
    except:
        return {"rate": 1350.0}

class SMSPostModel(BaseModel):
    stock_name: str
    signal_type: str
    price: float
    reason: str = "테스트 전송"

@app.post("/api/sms/test")
def api_test_sms(data: SMSPostModel):
    # Check enabled? User might want to force test even if disabled. 
    # Let's allow test.
    from sms import send_sms
    from datetime import datetime
    
    signal_time = datetime.now().strftime("%m/%d %H:%M")
    success = send_sms(
        stock_name=data.stock_name,
        signal_type=data.signal_type,
        price=data.price,
        signal_time=signal_time,
        reason=data.reason
    )
    
    msg = f"[{signal_time}] [{data.stock_name}] [{data.signal_type}] [${data.price}] [{data.reason}]"
    save_sms_log(receiver="01044900528", message=msg, status="Success" if success else "Failed")
    
    return {"status": "success" if success else "error"}

@app.get("/api/sms/history")
def api_get_sms_history(limit: int = 30):
    return get_sms_logs(limit=limit)

@app.delete("/api/sms/history/all")
def api_delete_all_sms_logs():
    if delete_all_sms_logs():
        return {"status": "success"}
    return {"status": "error"}

@app.delete("/api/sms/history/{id}")
def api_delete_sms_log(id: int):
    if delete_sms_log(id):
        return {"status": "success"}
    return {"status": "error"}

# [Ver 5.4] Manual Price Level Alerts API
class AlertLevelUpdate(BaseModel):
    ticker: str
    level_type: str
    stage: int
    price: float
    is_active: str

@app.get("/api/v2/alerts/{ticker}")
async def get_alerts(ticker: str):
    from db import get_price_levels
    levels = get_price_levels(ticker)
    return {"status": "success", "data": levels}

@app.post("/api/v2/alerts/update")
async def update_alert(item: AlertLevelUpdate):
    from db import update_price_level
    res = update_price_level(item.ticker, item.level_type, item.stage, item.price, item.is_active)
    if res:
        return {"status": "success"}
    return {"status": "error", "message": "Update failed"}

@app.post("/api/v2/alerts/reset")
async def reset_alert(item: AlertLevelUpdate):
    from db import reset_price_level_trigger
    res = reset_price_level_trigger(item.ticker, item.level_type, item.stage)
    if res:
        return {"status": "success"}
    return {"status": "error", "message": "Reset failed"}


# [Ver 5.9.1] Mini Chart Data API
@app.get("/api/v2/chart/{ticker}")
async def get_chart_data(ticker: str, limit: int = 50):
    """5분봉 기준 최근 N개 캔들 데이터 조회 (차트용)"""
    from db import get_mini_chart_data
    data = get_mini_chart_data(ticker.upper(), limit)
    return {"status": "success", "data": data}

# --- Stock APIs ---
class StockModel(BaseModel):
    code: str
    name: str
    is_active: bool = True

@app.get("/api/stocks")
def api_get_stocks():
    return get_stocks()

@app.post("/api/stocks")
def api_add_stock(stock: StockModel):
    if add_stock(stock.code, stock.name, stock.is_active):
        return {"status": "success"}
    return {"status": "error"}

class StockStatusModel(BaseModel):
    is_active: bool

@app.put("/api/stocks/{code}/status")
def api_update_stock_status(code: str, status: StockStatusModel):
    if update_stock_status(code, status.is_active):
        return {"status": "success"}
    return {"status": "error"}

@app.delete("/api/stocks/{code}")
def api_delete_stock(code: str):
    if delete_stock(code):
        return {"status": "success"}
    return {"status": "error"}

@app.post("/api/stocks/update-prices")
def api_update_stock_prices():
    """종목 현재가 즉시 업데이트 (사용자 요청)"""
    from db import update_stock_prices
    try:
        print(f"[{datetime.now()}] 사용자 요청: 종목 현재가 즉시 업데이트")
        result = update_stock_prices()
        if result:
            return {"status": "success", "message": "현재가 업데이트 완료"}
        return {"status": "error", "message": "현재가 업데이트 실패"}
    except Exception as e:
        print(f"현재가 즉시 업데이트 오류: {e}")
        return {"status": "error", "message": str(e)}


# --- Transaction APIs ---
class TransactionModel(BaseModel):
    id: int = None 
    ticker: str
    trade_type: str # BUY or SELL
    qty: int
    price: float
    trade_date: str
    memo: str = ""
    # [Ver 6.2] New fields
    category: str = "기타"
    group_name: Optional[str] = ""
    is_holding: Optional[bool] = True
    expected_sell_date: Optional[str] = None
    target_sell_price: Optional[float] = None
    strategy_memo: Optional[str] = ""

@app.get("/api/transactions")
def api_get_transactions():
    return get_transactions()

@app.post("/api/transactions")
def api_add_transaction(txn: TransactionModel):
    result = add_transaction(txn.dict())
    if isinstance(result, tuple):
        success, msg = result
        if success:
            return {"status": "success", "message": msg}
        else:
             return JSONResponse(status_code=400, content={"status": "error", "message": msg})
    # Fallback if boolean
    if result:
        return {"status": "success"}
    return JSONResponse(status_code=400, content={"status": "error", "message": "Transaction failed"})

@app.put("/api/transactions/{id}")
def api_update_transaction(id: int, txn: TransactionModel):
    if update_transaction(id, txn.dict()):
        return {"status": "success"}
    return {"status": "error"}

@app.delete("/api/transactions/{id}")
def api_delete_transaction(id: int):
    if delete_transaction(id):
        return {"status": "success"}
    return {"status": "error"}

# [Ver 6.3] Delete Holding
@app.delete("/api/holdings/{ticker}")
def remove_holding_endpoint(ticker: str):
    success, msg = delete_holding(ticker)
    if success:
        return {"status": "success", "message": msg}
    else:
        raise HTTPException(status_code=500, detail=msg)


# [Ver 6.5] Holding Update Model (Direct, No Journal)
class HoldingUpdateModel(BaseModel):
    qty: Optional[int] = 0
    quantity: Optional[int] = None # [Ver 7.5] Real Quantity
    manual_qty: Optional[int] = None # [Ver 6.8] Sim Quantity
    manual_price: Optional[float] = None
    price: Optional[float] = 0
    group_name: Optional[str] = ""
    is_holding: Optional[bool] = True
    expected_sell_date: Optional[str] = None
    target_sell_price: Optional[float] = None
    strategy_memo: Optional[str] = ""

@app.put("/api/holdings/{ticker}")
def update_holding_endpoint(ticker: str, data: HoldingUpdateModel):
    from db import update_holding_info
    # Unpack dict to keyword args
    success, msg = update_holding_info(ticker, **data.dict())
    if success:
        return {"status": "success", "message": msg}
    else:
        return JSONResponse(status_code=400, content={"status": "error", "message": msg})

@app.get("/api/transactions/stats")
def api_get_txn_stats():
    txns = get_transactions()
    if not txns: return []

    # Calculate Realized Profit based on FIFO
    inventory = {} 
    results = [] 
    
    # Sort by date asc
    txns_sorted = sorted(txns, key=lambda x: x['trade_date'])
    
    for t in txns_sorted:
        ticker = t['ticker']
        if ticker not in inventory: inventory[ticker] = []
        
        if t['trade_type'] == 'BUY':
            inventory[ticker].append({'price': t['price'], 'qty': t['qty'], 'date': t['trade_date']})
        elif t['trade_type'] == 'SELL':
            sell_qty = t['qty']
            sell_price = t['price']
            
            cost_basis = 0
            qty_filled = 0
            
            while sell_qty > 0 and inventory[ticker]:
                batch = inventory[ticker][0] # First item
                
                if batch['qty'] <= sell_qty:
                    cost_basis += batch['price'] * batch['qty']
                    qty_filled += batch['qty']
                    sell_qty -= batch['qty']
                    inventory[ticker].pop(0)
                else:
                    cost_basis += batch['price'] * sell_qty
                    qty_filled += sell_qty
                    batch['qty'] -= sell_qty
                    sell_qty = 0
            
            # If we sold something
            if qty_filled > 0:
                avg_buy_price = cost_basis / qty_filled
                profit = (sell_price - avg_buy_price) * qty_filled
                pct = ((sell_price - avg_buy_price) / avg_buy_price) * 100
                
                results.append({
                    "ticker": ticker,
                    "date": t['trade_date'],
                    "qty": qty_filled,
                    "profit": round(profit, 2),
                    "pct": round(pct, 2)
                })
                
    return results

@app.get("/api/requests")
async def get_requests():
    """Get all tracked user requests"""
    try:
        from db import get_user_requests
        reqs = get_user_requests()
        return reqs
    except Exception as e:
        print(f"Get Requests Error: {e}")
        return []

class RequestItem(BaseModel):
    request_text: str
    ai_interpretation: str
    implementation_details: str

@app.post("/api/requests")
async def create_request(item: RequestItem):
    """Log a new user request"""
    try:
        from db import add_user_request
        add_user_request(item.request_text, item.ai_interpretation, item.implementation_details)
        return {"status": "success"}
    except Exception as e:
        print(f"Add Request Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Auth APIs ---
class UserRegister(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

@app.post("/api/auth/register")
def register_api(user: UserRegister):
    from db import create_user, get_user_by_email
    try:
        print(f"DEBUG: Register API called for {user.email}")
        existing = get_user_by_email(user.email)
        print(f"DEBUG: get_user_by_email result: {existing}")
        
        if existing:
            return {"status": "error", "message": f"이미 존재하는 이메일입니다: {user.email}"}
        
        print(f"DEBUG: Creating user {user.name}")
        hashed_pw = pbkdf2_sha256.hash(user.password)
        if create_user(user.email, hashed_pw, user.name):
            return {"status": "success", "message": "회원가입 성공"}
        
        return {"status": "error", "message": "회원가입 DB 처리 실패"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"서버 오류: {str(e)}"}

@app.post("/api/auth/login")
def login_api(user: UserLogin):
    from db import get_user_by_email
    try:
        db_user = get_user_by_email(user.email)
        if not db_user:
            return {"status": "error", "message": "이메일 또는 비밀번호가 올바르지 않습니다."}
        
        if not pbkdf2_sha256.verify(user.password, db_user['password_hash']):
            return {"status": "error", "message": "이메일 또는 비밀번호가 올바르지 않습니다."}
        
        # Create JWT
        # UTC issue: datetime.utcnow() is deprecated in some versions but safe for JWT usually
        exp = datetime.utcnow() + timedelta(days=30) # 30일 접속 유지 (요청사항)
        
        token_data = {
            "sub": db_user['email'],
            "name": db_user['name'],
            "exp": exp
        }
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        
        return {
            "status": "success",
            "token": token,
            "user": {"email": db_user['email'], "name": db_user['name']}
        }
    except Exception as e:
        print(f"Login Error: {e}")
        return {"status": "error", "message": "로그인 처리 중 오류 발생"}

@app.get("/api/auth/me")
def me_api(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"status": "success", "user": {"email": payload['sub'], "name": payload['name']}}
    except jwt.ExpiredSignatureError:
        return {"status": "error", "message": "Token expired"}
    except jwt.InvalidTokenError:
        return {"status": "error", "message": "Invalid token"}

@app.get("/api/v2/status/{ticker}")
def get_v2_status(ticker: str):
    """Get V2 Signal Status (Buy/Sell) + Market Info"""
    try:
        from db import get_v2_buy_status, get_v2_sell_status, get_market_indices, get_latest_market_indicators, get_stock_current_price
        ticker = ticker.upper()
        
        buy_record = get_v2_buy_status(ticker)
        sell_record = get_v2_sell_status(ticker)
        
        # [Ver 5.7] Get current_price from managed_stocks (Active Update Source)
        # market_indices is restricted to indices only (SPX, VIX, etc)
        price_info = get_stock_current_price(ticker)
        
        if price_info:
             current_price = float(price_info['price'])
             # [Ver 6.9] Use retrieved change_pct
             change_pct = float(price_info.get('change_pct', 0.0))
        else:
             # Fallback to market_indices (Old Logic / For pure indices)
             market_data = get_market_indices()
             market_info = next((m for m in market_data if m['ticker'] == ticker), None)
             current_price = float(market_info['current_price']) if market_info else 0.0
             change_pct = float(market_info.get('change_pct', 0.0)) if market_info else 0.0

        # [Ver 5.7.3] Inject Day High & Score from Cached Analysis
        day_high = 0.0
        current_score = 0.0
        try:
            from analysis import get_cached_report
            cached = get_cached_report()
            if cached and 'stocks' in cached:
                stock_data = next((s for s in cached['stocks'] if s['ticker'] == ticker), None)
                if stock_data:
                    day_high = float(stock_data.get('day_high', 0.0))
                    current_score = float(stock_data.get('score', 0.0))
            print(f"DEBUG: {ticker} cached info: high={day_high}, score={current_score}")
        except Exception as e:
            print(f"DEBUG Error getting cached values: {e}")
            pass


        # Get latest indicators for metrics display
        indicators = get_latest_market_indicators(ticker)
        
        # Convert decimals to float for JSON serialization
        def serialize(obj):
            if not obj: return None
            # Ensure obj is a dict, not a list
            if isinstance(obj, list):
                return None
            # If it's already a dict, use it; otherwise convert
            new_obj = obj if isinstance(obj, dict) else dict(obj)
            for k, v in new_obj.items():
                from decimal import Decimal
                from datetime import datetime
                if isinstance(v, Decimal):
                    new_obj[k] = float(v)
                elif isinstance(v, datetime):
                    new_obj[k] = v.isoformat()
            return new_obj

        # [Ver 6.5.8] BBI 계산 추가
        bbi_info = {'bbi': 0, 'adx': 0, 'bbw_ratio': 1.0, 'status': '계산 중'}
        try:
            from analysis import calculate_bbi, fetch_data
            data_30m, _, _, _, _ = fetch_data([ticker], force=False)
            if data_30m and ticker in data_30m:
                df_30 = data_30m[ticker]
                if df_30 is not None and not df_30.empty:
                    bbi_info = calculate_bbi(df_30)
        except Exception as e:
            print(f"BBI Calc Error in API: {e}")

        return {
            "status": "success",
            "buy": serialize(buy_record),
            "sell": serialize(sell_record),
            "market_info": {
                "current_price": current_price,
                "change_pct": change_pct,
                "day_high": day_high,
                "current_score": current_score
            },
            "metrics": serialize(indicators),  # Add metrics from market_indicators_log
            "bbi": bbi_info  # [Ver 6.5.8] BBI 정보 추가
        }
    except Exception as e:
        print(f"V2 Status Error: {e}")
        return {"status": "error", "message": str(e)}

# --- Trade Confirmation Endpoints ---

class ConfirmTradeModel(BaseModel):
    ticker: str  # Changed from manage_id
    price: float
    qty: float
    is_end: bool = False

class UpdateTargetModel(BaseModel):
    ticker: str  # Changed from manage_id
    target_type: str  # 'box', 'stop'
    price: float

@app.post("/api/v2/update-target")
def api_update_target(data: UpdateTargetModel):
    from db import update_v2_target_price
    # Use ticker instead of manage_id
    if update_v2_target_price(data.ticker, data.target_type, data.price):
        return {"status": "success", "message": "Target Price Updated"}
    else:
        return {"status": "error", "message": "Failed to update target price"}

@app.post("/api/v2/confirm-buy")
def api_confirm_buy(data: ConfirmTradeModel):
    from db import confirm_v2_buy
    try:
        # Use ticker instead of manage_id
        success, msg = confirm_v2_buy(data.ticker, data.price, data.qty)
        if success:
            return {"status": "success", "message": "Buy Confirmed"}
        else:
            return {"status": "error", "message": msg}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/v2/confirm-sell")
def api_confirm_sell(data: ConfirmTradeModel):
    from db import confirm_v2_sell
    try:
        # Use ticker instead of manage_id
        success, msg = confirm_v2_sell(data.ticker, data.price, data.qty, data.is_end)
        if success:
            return {"status": "success", "message": "Sell Confirmed"}
        else:
            return {"status": "error", "message": msg}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class ManualSignalModel(BaseModel):
    ticker: str
    signal_key: str
    price: float
    status: str = 'Y'
    qty: float = 0.0  # [Ver 7.3.1] Add Quantity for Partial Real Buy

@app.post("/api/v2/manual-signal")
def api_manual_signal(data: ManualSignalModel):
    from db import manual_update_signal, get_v2_buy_status
    try:
        print(f"DEBUG: Manual Signal Request: Ticker={data.ticker}, Key={data.signal_key}, Status={data.status}, Qty={data.qty}")
        
        # [DEBUG] Check Buy Status Before
        buy_before = get_v2_buy_status(data.ticker)
        b2_before = buy_before.get('buy_sig2_yn', 'N') if buy_before else 'None'

        # Use ticker instead of manage_id
        # [Ver 7.3.1] Pass qty to manual_update_signal
        success = manual_update_signal(data.ticker, data.signal_key, data.price, data.status, qty=data.qty)
        
        # [DEBUG] Check Buy Status After
        buy_after = get_v2_buy_status(data.ticker)
        b2_after = buy_after.get('buy_sig2_yn', 'N') if buy_after else 'None'
        print(f"DEBUG: Buy2 After: {b2_after} (Success={success})")

        if success:
            return {"status": "success", "message": "Signal Updated"}
        else:
            return {"status": "error", "message": "Update Failed (Invalid Key/Ticker?)"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/api/v2/record/{ticker}")
def api_delete_record(ticker: str):
    from db import delete_v2_record
    try:
        # Use ticker instead of manage_id
        success = delete_v2_record(ticker)
        if success:
            return {"status": "success", "message": "Record Deleted"}
        else:
            return {"status": "error", "message": "Delete Failed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/api/v2/sell-record/{ticker}")
def api_delete_sell_record(ticker: str):
    from db import delete_v2_sell_only
    try:
        # Use ticker instead of manage_id
        success = delete_v2_sell_only(ticker)
        if success:
            return {"status": "success", "message": "Sell Record Deleted"}
        else:
            return {"status": "error", "message": "Delete Failed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}



# ========================================
# Trading Journal (거래일지) API Endpoints
# ========================================

class TradeJournalCreate(BaseModel):
    ticker: str
    buy_date: str
    buy_price: float
    buy_qty: int = 1
    buy_reason: str = None
    market_condition: str = None
    prediction_score: str = None
    total_assets: float = None
    score_at_entry: int = None
    tags: str = None
    screenshot: Optional[str] = None  # Base64 encoded image

class TradeJournalUpdate(BaseModel):
    sell_date: str = None
    sell_price: float = None
    sell_qty: int = None
    sell_reason: str = None
    market_condition: str = None
    prediction_score: str = None
    total_assets: float = None
    emotion_after: str = None
    score_at_entry: int = None
    score_at_exit: int = None
    realized_pnl: float = None
    realized_pnl_pct: float = None
    hold_days: int = None
    lesson: str = None
    tags: str = None
    status: str = None
    buy_date: str = None
    buy_price: float = None
    buy_qty: int = None
    buy_reason: str = None
    screenshot: str = None

@app.get("/api/journal")
def get_journals(status: str = None, ticker: str = None, limit: int = 100):
    """거래일지 목록 조회"""
    from db import get_trade_journals
    journals = get_trade_journals(status=status, ticker=ticker, limit=limit)
    # Convert datetime objects to ISO strings for JSON
    for j in journals:
        for key in ['buy_date', 'sell_date', 'created_at', 'updated_at']:
            if j.get(key) and hasattr(j[key], 'isoformat'):
                j[key] = j[key].isoformat()
    return journals

@app.get("/api/journal/stats")
def get_journal_stats():
    """거래일지 통계 조회"""
    from db import get_trade_journal_stats
    return get_trade_journal_stats()

@app.get("/api/journal/{journal_id}")
def get_journal(journal_id: int):
    """단일 거래 조회"""
    from db import get_trade_journal_by_id
    journal = get_trade_journal_by_id(journal_id)
    if not journal:
        return {"error": "Not found"}
    # Convert datetime
    for key in ['buy_date', 'sell_date', 'created_at', 'updated_at']:
        if journal.get(key) and hasattr(journal[key], 'isoformat'):
            journal[key] = journal[key].isoformat()
    return journal

@app.post("/api/journal")
def create_journal(data: TradeJournalCreate):
    """새 거래 기록 생성"""
    from db import create_trade_journal
    journal_id = create_trade_journal(data.model_dump())
    if journal_id:
        return {"status": "success", "id": journal_id}
    return {"status": "error", "message": "Failed to create journal"}

@app.put("/api/journal/{journal_id}")
def update_journal(journal_id: int, data: TradeJournalUpdate):
    """거래 수정 (청산 정보 추가 포함)"""
    from db import update_trade_journal, get_trade_journal_by_id
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    # Auto-calculate realized PnL if closing trade
    if update_data.get('sell_price') and update_data.get('status') == 'CLOSED':
        journal = get_trade_journal_by_id(journal_id)
        if journal:
            buy_price = float(journal['buy_price'])
            buy_qty = int(journal['buy_qty'])
            sell_price = float(update_data['sell_price'])
            sell_qty = int(update_data.get('sell_qty', buy_qty))
            
            # Calculate P&L
            cost = buy_price * buy_qty
            revenue = sell_price * sell_qty
            pnl = revenue - cost
            pnl_pct = (pnl / cost) * 100 if cost > 0 else 0
            
            update_data['realized_pnl'] = round(pnl, 2)
            update_data['realized_pnl_pct'] = round(pnl_pct, 2)
            
            # Calculate hold days
            if journal.get('buy_date') and update_data.get('sell_date'):
                from datetime import datetime
                buy_dt = journal['buy_date'] if isinstance(journal['buy_date'], datetime) else datetime.fromisoformat(str(journal['buy_date']))
                sell_dt = datetime.fromisoformat(update_data['sell_date'])
                update_data['hold_days'] = (sell_dt - buy_dt).days
    
    success = update_trade_journal(journal_id, update_data)
    if success:
        return {"status": "success"}
    return {"status": "error", "message": "Failed to update journal"}

@app.delete("/api/journal/{journal_id}")
def delete_journal(journal_id: int):
    """거래 삭제"""
    from db import delete_trade_journal
    success = delete_trade_journal(journal_id)
    if success:
        return {"status": "success"}
    return {"status": "error", "message": "Failed to delete journal"}

# ========================================
# Daily Assets (일별 자산) API Endpoints
# ========================================

class DailyAssetCreate(BaseModel):
    record_date: str
    total_assets: float
    daily_return_pct: Optional[float] = None  # 수익률 (%)
    daily_pnl: Optional[float] = None  # 손익 (원)
    note: Optional[str] = None

@app.get("/api/assets")
def get_assets(start_date: str = None, end_date: str = None, limit: int = 365):
    """일별 자산 목록 조회"""
    from db import get_daily_assets
    assets = get_daily_assets(start_date=start_date, end_date=end_date, limit=limit)
    # Convert date objects
    for a in assets:
        if a.get('record_date'):
            a['record_date'] = str(a['record_date'])
    return assets

@app.post("/api/assets")
def create_asset(data: DailyAssetCreate):
    """일별 자산 등록/수정"""
    from db import upsert_daily_asset
    success = upsert_daily_asset(
        record_date=data.record_date,
        total_assets=data.total_assets,
        daily_return_pct=data.daily_return_pct,
        daily_pnl=data.daily_pnl,
        note=data.note
    )
    if success:
        return {"status": "success"}
    return {"status": "error", "message": "Failed to save asset"}

@app.get("/api/assets/summary")
def get_assets_summary():
    """자산 요약 통계"""
    from db import get_asset_summary
    summary = get_asset_summary()
    # Convert dates
    if summary.get('latest') and summary['latest'].get('record_date'):
        summary['latest']['record_date'] = str(summary['latest']['record_date'])
    if summary.get('active_goal') and summary['active_goal'].get('target_date'):
        summary['active_goal']['target_date'] = str(summary['active_goal']['target_date'])
    return summary

@app.delete("/api/assets/{record_date}")
def delete_asset(record_date: str):
    """일별 자산 삭제"""
    from db import delete_daily_asset
    success = delete_daily_asset(record_date)
    if success:
        return {"status": "success"}
    return {"status": "error", "message": "Failed to delete asset"}

# ========================================
# Asset Goals (목표 금액) API Endpoints
# ========================================


class AssetGoalCreate(BaseModel):
    goal_name: str
    target_amount: float
    target_date: Optional[str] = None

class AssetGoalUpdate(BaseModel):
    goal_name: Optional[str] = None
    target_amount: Optional[float] = None
    target_date: Optional[str] = None
    is_active: Optional[bool] = None

@app.get("/api/goals")
def get_goals():
    """목표 금액 목록 조회"""
    from db import get_asset_goals
    goals = get_asset_goals()
    for g in goals:
        if g.get('target_date'):
            g['target_date'] = str(g['target_date'])
    return goals

@app.post("/api/goals")
def create_goal(data: AssetGoalCreate):
    """목표 금액 등록"""
    from db import create_asset_goal
    goal_id = create_asset_goal(
        goal_name=data.goal_name,
        target_amount=data.target_amount,
        target_date=data.target_date
    )
    if goal_id:
        return {"status": "success", "id": goal_id}
    return {"status": "error", "message": "Failed to create goal"}

@app.put("/api/goals/{goal_id}")
def update_goal(goal_id: int, data: AssetGoalUpdate):
    """목표 금액 수정"""
    from db import update_asset_goal
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    success = update_asset_goal(goal_id, update_data)
    if success:
        return {"status": "success"}
    return {"status": "error", "message": "Failed to update goal"}

@app.delete("/api/goals/{goal_id}")
def delete_goal(goal_id: int):
    """목표 금액 삭제"""
    from db import delete_asset_goal
    success = delete_asset_goal(goal_id)
    if success:
        return {"status": "success"}
    return {"status": "error", "message": "Failed to delete goal"}

# ========================================
# Trading Strategies (전략) API Endpoints
# ========================================


class StrategyCreate(BaseModel):
    strategy_name: str
    description: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None
    initial_assets: Optional[float] = None
    target_assets: Optional[float] = None
    target_return_pct: Optional[float] = None
    status: str = "ACTIVE"

class StrategyUpdate(BaseModel):
    strategy_name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_assets: Optional[float] = None
    target_assets: Optional[float] = None
    target_return_pct: Optional[float] = None
    status: Optional[str] = None

@app.get("/api/strategies")
def get_strategies(status: str = None):
    """전략 목록 조회"""
    from db import get_trading_strategies
    strategies = get_trading_strategies(status=status)
    for s in strategies:
        for key in ['start_date', 'end_date', 'created_at', 'updated_at']:
            if s.get(key) and hasattr(s[key], 'isoformat'):
                s[key] = s[key].isoformat()
            elif s.get(key):
                s[key] = str(s[key])
    return strategies

@app.get("/api/strategies/{strategy_id}")
def get_strategy(strategy_id: int):
    """전략 상세 조회"""
    from db import get_trading_strategy_by_id
    strategy = get_trading_strategy_by_id(strategy_id)
    if not strategy:
        return {"error": "Not found"}
    for key in ['start_date', 'end_date', 'created_at', 'updated_at']:
        if strategy.get(key) and hasattr(strategy[key], 'isoformat'):
            strategy[key] = strategy[key].isoformat()
    return strategy

@app.post("/api/strategies")
def create_strategy(data: StrategyCreate):
    """전략 등록"""
    from db import create_trading_strategy
    strategy_id = create_trading_strategy(data.dict())
    if strategy_id:
        return {"status": "success", "id": strategy_id}
    return {"status": "error", "message": "Failed to create strategy"}

@app.put("/api/strategies/{strategy_id}")
def update_strategy(strategy_id: int, data: StrategyUpdate):
    """전략 수정"""
    from db import update_trading_strategy
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    success = update_trading_strategy(strategy_id, update_data)
    if success:
        return {"status": "success"}
    return {"status": "error", "message": "Failed to update strategy"}

@app.delete("/api/strategies/{strategy_id}")
def delete_strategy(strategy_id: int):
    """전략 삭제"""
    from db import delete_trading_strategy
    success = delete_trading_strategy(strategy_id)
    if success:
        return {"status": "success"}
    return {"status": "error", "message": "Failed to delete strategy"}

@app.get("/api/strategies/{strategy_id}/performance")
def get_strategy_perf(strategy_id: int):
    """전략 성과 분석"""
    from db import get_strategy_performance
    perf = get_strategy_performance(strategy_id)
    if not perf:
        return {"error": "Not found or no data"}
    # Convert dates in strategy
    if perf.get('strategy'):
        for key in ['start_date', 'end_date', 'created_at', 'updated_at']:
            if perf['strategy'].get(key) and hasattr(perf['strategy'][key], 'isoformat'):
                perf['strategy'][key] = perf['strategy'][key].isoformat()
            elif perf['strategy'].get(key):
                perf['strategy'][key] = str(perf['strategy'][key])
    return perf

# --- Auto Trading Log Endpoints (Ver 5.9.3) ---
@app.get("/api/trading/status")
def api_get_trading_status():
    from db import get_open_trade
    trades = []
    for t in ['SOXL', 'SOXS']:
        row = get_open_trade(t)
        if row:
            # Serialise
            for k in ['entry_time', 'exit_time', 'created_at']:
                if row.get(k): row[k] = row[k].isoformat()
            
            for k in ['entry_price', 'exit_price', 'profit_pct']:
               if row.get(k): row[k] = float(row[k])
            trades.append(row)
    return trades

@app.get("/api/trading/history")
def api_get_trading_history(limit: int = 50):
    from db import get_trade_history
    import pytz
    from datetime import datetime
    
    rows = get_trade_history(limit)
    
    # [Ver 8.1.0] Convert to NY Time for Display
    tz_kr = pytz.timezone('Asia/Seoul')
    tz_ny = pytz.timezone('America/New_York')
    
    result = []
    for row in rows:
        # Convert Timezones
        for k in ['entry_time', 'exit_time', 'created_at']:
            val = row.get(k)
            if val and isinstance(val, datetime):
                # Assume DB saves in System Time (KST usually)
                if val.tzinfo is None:
                    # If naive, assume KST (Server Time)
                    # We should verify if server is UTC or KST. 
                    # Previous logs showed +0900.
                    val = tz_kr.localize(val)
                
                # Convert to NY
                val_ny = val.astimezone(tz_ny)
                row[k] = val_ny.strftime('%Y-%m-%d %H:%M:%S') # String format explicitly
            elif val:
                row[k] = str(val)

        for k in ['entry_price', 'exit_price', 'profit_pct']:
            if row.get(k): row[k] = float(row[k])
            
        result.append(row)
    return result

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9100, reload=True)

