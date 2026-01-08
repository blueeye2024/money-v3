import requests
from datetime import datetime

def send_sms(stock_name, signal_type, price, signal_time, reason=""):
    """
    Send SMS using the provided API endpoint.
    Format: [신호 발생시간] [종목이름] [매수/매도] [가격] [사유]
    """
    url = "http://sms.nanuminet.com/utf8.php"
    
    # Format current time for senddate
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # [FIX] Enforce Global SMS Check
    try:
        from db import get_global_config
        if not get_global_config("sms_enabled", True):
            print(f"SMS Skipped (Global OFF): {stock_name} {signal_type}")
            return False
    except ImportError:
        pass # Fallback if db import fails (e.g. testing)

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
        # "phone[]": "01044900528", # Target Phone Number? User code commented it out, but usually required. 
        # Assuming the API might use a default or it was hidden. 
        # Let's use the number from the comment assuming it's the valid target.
        "phone[]": "01044900528", 
        "msg[]": msg
    }
    
    try:
        # requests.post default content-type is form-urlencoded for dict data
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            print(f"SMS Sent: {msg}")
            return True
        else:
            print(f"SMS Failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"SMS Error: {e}")
        return False
