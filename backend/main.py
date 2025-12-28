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
from db import init_db, save_signal, check_last_signal, get_stocks, add_stock, delete_stock, add_transaction, get_transactions, update_transaction, delete_transaction, get_signals, save_sms_log, get_sms_logs

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
                
                is_new = True
                current_raw_time = res.get('signal_time_raw')
                
                if current_raw_time is None: continue

                if last_sig:
                    last_time = last_sig['signal_time']
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
                    reason = f"RSI:{res['rsi']:.1f}"
                    success = send_sms(
                        stock_name=res['name'], 
                        signal_type=res['position'], 
                        price=res['current_price'], 
                        signal_time=res['signal_time'], 
                        reason=reason
                    )
                    
                    msg = f"[{res['signal_time']}] [{res['name']}] [{res['position']}] [${res['current_price']}] [{reason}]"
                    save_sms_log(receiver="01044900528", message=msg, status="Success" if success else "Failed")

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

@app.get("/api/signals")
def api_get_signals(ticker: str = None, start_date: str = None, end_date: str = None, limit: int = 30):
    return get_signals(ticker, start_date, end_date, limit)

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
def api_get_sms_history():
    return get_sms_logs(limit=30)

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

# --- Transaction APIs ---
class TransactionModel(BaseModel):
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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
