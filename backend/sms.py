import requests
from datetime import datetime


# In-Memory Cache for SMS Cooldown (Key: Ticker, Value: datetime of last send)
SMS_SENT_CACHE = {}

def send_sms(stock_name, signal_type, price, signal_time, reason=""):
    """
    Send SMS using the provided API endpoint.
    Format: [신호 발생시간] [종목이름] [매수/매도] [가격] [사유]
    """
    # [FILTER] Update 1: Send ONLY for 'Triple Filter Complete' (Final Buy)
    # The system uses "BUY (MASTER)" for the final triple filter signal.
    # We also check for "Triple Filter" just in case the string varies.
    if "MASTER" not in signal_type and "Triple Filter" not in signal_type:
        # print(f"SMS Skipped (Filter): {stock_name} {signal_type} is not a Master Signal")
        return False

    url = "http://sms.nanuminet.com/utf8.php"
    
    # Format current time for senddate
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # [FIX] Update 2: Enforce Global SMS Check (Default to FALSE to prevent Ghost Toggle)
    try:
        from db import get_global_config
        # CHANGED default from True to False
        if not get_global_config("sms_enabled", False):
            print(f"SMS Skipped (Global OFF): {stock_name} {signal_type}")
            return False
    except ImportError:
        pass # Fallback if db import fails (e.g. testing)

    # [FIX] Update 3: 30-Minute Cooldown per Ticker
    last_sent = SMS_SENT_CACHE.get(stock_name)
    if last_sent:
        elapsed = (now - last_sent).total_seconds()
        if elapsed < 1800: # 30 minutes * 60 seconds
            print(f"SMS Skipped (Cooldown): {stock_name} sent {int(elapsed/60)}m ago.")
            return False

    # Format message
    # User Request: Remove Time from Body.
    # Msg Format: [SOXL] [매수] [45.20] [85점]
    msg = f"[{stock_name}] [{signal_type}] [${price}] [{reason}]"
    
    data = {
        "sms_id": "leeyw94",
        "sms_pw": "blueeye0037!",
        "callback": "070-8244-8202",
        "senddate": now_str,
        "return_url": "https://myworkpage.kr/sys/sms_end",
        "return_data": "",
        "use_mms": "Y",
        "upFile": "",
        "phone[]": "01044900528", 
        "msg[]": msg
    }
    
    try:
        # requests.post default content-type is form-urlencoded for dict data
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            print(f"SMS Sent: {msg}")
            # Update Cache on Success
            SMS_SENT_CACHE[stock_name] = now
            return True
        else:
            print(f"SMS Failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"SMS Error: {e}")
        return False

