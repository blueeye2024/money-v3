from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pandas as pd
import pytz
import uvicorn

from analysis import run_analysis, fetch_data, analyze_ticker, TARGET_TICKERS
from sms import send_sms
from db import init_db, save_signal, check_last_signal, get_stocks, add_stock, delete_stock, add_transaction, get_transactions, update_transaction, delete_transaction, get_signals, save_sms_log, get_sms_logs, delete_all_signals, delete_sms_log, delete_all_sms_logs, get_ticker_settings, update_ticker_setting

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
    from db import init_db, get_global_config
    init_db()
    
    # Load SMS Setting from DB
    global SMS_ENABLED
    SMS_ENABLED = get_global_config("sms_enabled", True)
    print(f"Startup: SMS Enabled = {SMS_ENABLED}")

    # Start Scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(monitor_signals, 'interval', minutes=1)  # 신호 모니터링 (1분)
    scheduler.add_job(update_prices_job, 'interval', minutes=5)  # 종목 현재가 업데이트 (5분)
    scheduler.start()

# Global SMS Control (Now persistent via DB)
SMS_ENABLED = True
SMS_THROTTLE_MINUTES = 30

class SMSSettingModel(BaseModel):
    enabled: bool

class TickerSettingUpdate(BaseModel):
    ticker: str
    is_visible: bool

class CapitalModel(BaseModel):
    amount: float

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
        return {"amount": get_total_capital()}
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

# 2. Monitor Logic (Runs every 1 min)
def update_prices_job():
    """5분마다 종목 현재가 업데이트"""
    from db import update_stock_prices
    try:
        print(f"[{datetime.now()}] 종목 현재가 업데이트 시작...")
        update_stock_prices()
    except Exception as e:
        print(f"현재가 업데이트 작업 오류: {e}")

def monitor_signals():
    global SMS_ENABLED
    print(f"[{datetime.now()}] Monitoring Signals... SMS Enabled: {SMS_ENABLED}")
    
    try:
        # Use run_analysis for all processing to ensure consistency with dashboard
        full_report = run_analysis()
        stocks_data = full_report.get('stocks', [])
        
        for stock_res in stocks_data:
            ticker = stock_res['ticker']
            res = stock_res # Use the result from run_analysis
            
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
                        if diff_mins < 30 and last_sig['position'] == res['position']:
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
                            signal_time=m_res.get('signal_time', '지금'),
                            reason="3종 필터 완성"
                        )
                        save_sms_log(receiver="01044900528", message=f"[{k_ticker}] [{m_pos}] 완성", status="Success")

                # B. 5m Dead Cross Warning (Warning 5m)
                if m_res.get('warning_5m'):
                    from db import check_recent_sms_log
                    w_pos = f"{k_ticker} 5분봉 경고"
                    recent_w = check_recent_sms_log(k_ticker, w_pos, 30)
                    
                    if not recent_w and SMS_ENABLED:
                        send_sms(
                            stock_name=k_ticker,
                            signal_type="주의 경보",
                            price=full_report['holdings'].get(k_ticker, {}).get('current_price', 0),
                            signal_time="현재",
                            reason="5분봉 데드크로스 발생"
                        )
                        save_sms_log(receiver="01044900528", message=f"[{k_ticker}] [{w_pos}] 주의!!", status="Success")

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

    except Exception as e:
        print(f"Monitor Error: {e}")
        import traceback
        traceback.print_exc()

@app.get("/api/report")
def get_report():
    try:
        from db import get_current_holdings, get_ticker_settings
        holdings = get_current_holdings()
        settings = get_ticker_settings()

        # Run standard analysis
        data = run_analysis(holdings)
        
        # Add visibility flag to each stock
        for stock in data.get('stocks', []):
            ticker = stock['ticker']
            stock['is_visible'] = settings.get(ticker, True) # Default to True
        
        # Old Mock Insight Removed. Prefer analysis.py's Trade Guidelines.
        # Ensure data['insight'] exists; it should from run_analysis.
        if 'insight' not in data:
            data['insight'] = "데이터 분석 중..."

        
        return data
    except Exception as e:
        print(f"Error: {e}")
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

# --- Stock APIs ---
class StockModel(BaseModel):
    code: str
    name: str

@app.get("/api/stocks")
def api_get_stocks():
    return get_stocks()

@app.post("/api/stocks")
def api_add_stock(stock: StockModel):
    if add_stock(stock.code, stock.name):
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

@app.get("/api/transactions")
def api_get_transactions():
    return get_transactions()

@app.post("/api/transactions")
def api_add_transaction(txn: TransactionModel):
    if add_transaction(txn.dict()):
        return {"status": "success"}
    return {"status": "error"}

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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
