from fastapi import APIRouter, HTTPException
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz

router = APIRouter(
    prefix="/api/crypto",
    tags=["crypto"]
)

# Supported Coins
COINS = {
    "BTC": "BTC-USD",
    "XRP": "XRP-USD"
}

@router.get("/status")
def get_crypto_status():
    """
    Get current price, daily change, and timestamp (KST) for XRP and BTC.
    """
    # Desired Order: XRP, BTC
    ordered_coins = ["XRP", "BTC"]
    results = []
    
    # KST Time
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")

    for symbol in ordered_coins:
        try:
            ticker = COINS.get(symbol)
            if not ticker: continue
            
            # Use yfinance 'Ticker' object
            obj = yf.Ticker(ticker)
            # Fast fetch using fast_info or history
            # fast_info is better for current price
            price = 0.0
            change_pct = 0.0
            
            try:
                # Attempt fast_info first (newer yf)
                info = obj.fast_info
                price = info.last_price
                prev_close = info.previous_close
                if prev_close > 0:
                    change_pct = ((price - prev_close) / prev_close) * 100
            except:
                # Fallback to history (1d)
                hist = obj.history(period="2d")
                if len(hist) >= 1:
                    price = float(hist['Close'].iloc[-1])
                    if len(hist) >= 2:
                        prev = float(hist['Close'].iloc[-2])
                        change_pct = ((price - prev) / prev) * 100
                        
            results.append({
                "symbol": symbol,
                "price": price,
                "change": change_pct,
                "name": ticker,
                "time": now_kst  # Add Timestamp
            })
        except Exception as e:
            print(f"Crypto Status Error ({symbol}): {e}")
            results.append({
                "symbol": symbol,
                "price": 0.0,
                "change": 0.0,
                "time": now_kst,
                "error": str(e)
            })
            
    return {"data": results}

@router.get("/history/{symbol}")
def get_crypto_history(symbol: str, period: str = "daily"):
    """
    Get chart data. 
    period: 'daily' (Last 30 days) or '30m' (Last 5 days 30m)
    """
    if symbol not in COINS:
        raise HTTPException(status_code=404, detail="Coin not supported")
    
    ticker = COINS[symbol]
    obj = yf.Ticker(ticker)
    
    try:
        df = pd.DataFrame()
        
        if period == 'daily':
            # Daily Chart (Last 60 days for trend)
            df = obj.history(period="60d", interval="1d")
        elif period == '30m':
            # 30m Chart (Last 5 days - limit of yfinance 1m/Intraday)
            # 30m can obtain last 60d actually, but 5-7 days is enough for dashboard
            df = obj.history(period="5d", interval="30m")
        
        if df.empty:
            return {"data": []}
            
        # Format for Recharts
        data = []
        for idx, row in df.iterrows():
            # index is datetime
            ts = idx
            # Convert to KST for display? Or keep local/UTC?
            # Usually charts expect specific string or timestamp. 
            # Recharts handles simple strings well.
            
            # Format: 'MM/DD' for daily, 'DD HH:MM' for 30m
            time_str = ""
            if period == 'daily':
                time_str = ts.strftime('%m/%d')
            else:
                # Convert to KST
                ts_kst = ts.tz_convert('Asia/Seoul') if ts.tzinfo else ts
                time_str = ts_kst.strftime('%d日 %H:%M')
                
            data.append({
                "time": time_str,
                "full_date": str(ts),
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": float(row['Volume'])
            })
            
        return {"symbol": symbol, "data": data}
        
    except Exception as e:
        print(f"Crypto History Error: {e}")
        return {"data": []}

# [Ver 7.6] Crypto Settings (Holdings & Limits) in DB
from pydantic import BaseModel
from typing import Dict, Any, Optional

class CryptoSettingsModel(BaseModel):
    holdings: Optional[Dict[str, float]] = {}
    limits: Optional[Dict[str, Dict[str, Any]]] = {}

@router.get("/settings")
def get_crypto_settings():
    from db import get_global_config
    settings = get_global_config("crypto_settings", {"holdings": {}, "limits": {}})
    return {"status": "success", "data": settings}

@router.post("/settings")
def update_crypto_settings(settings: CryptoSettingsModel):
    from db import set_global_config, get_global_config
    
    # Merge logic: Read existing -> Update provided fields -> Save
    current = get_global_config("crypto_settings", {"holdings": {}, "limits": {}})
    
    if settings.holdings is not None:
        current["holdings"] = settings.holdings
    if settings.limits is not None:
        current["limits"] = settings.limits
        
    if set_global_config("crypto_settings", current):
        return {"status": "success", "data": current}
    return {"status": "error", "message": "Failed to save settings"}
