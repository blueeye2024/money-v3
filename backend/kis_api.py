import requests
import json
import time
import os
import fcntl
from datetime import datetime, timedelta

class KisApi:
    def __init__(self):
        self.APP_KEY = "PS9q8I7TgXLRu2XNJj2GZnaqGU2Uy1CtDZpI"
        self.APP_SECRET = "KSgC+E/xD+fvGhquv0DLXXKXf9jD4c4jOLZLWuLCp004H+vx9RSQbcPR3CGO0Ox3SHhCykiaDgmjYM0grzH2/j9rnVUGa9GqylNLEFxBq9dYtGhCe01pZ4hGqn4j/U5raqWkQBYWwtzT3Hy/VOZ8eKWooJgbyH5gGygZuUifV7uVnYfMPec="
        self.URL_BASE = "https://openapi.koreainvestment.com:9443"
        self.token_file = "kis_token.json"
        
        # Initial Load
        self.access_token = self._load_token()

    def _load_token(self):
        """Load token from file or request new one"""
        token = self._read_token_from_file()
        if token:
            return token
        return self._issue_token()

    def _read_token_from_file(self, buffer_sec=60):
        """Pure file read with expiry check"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    # Check expiry
                    expiry_dt = datetime.strptime(data['expiry'], "%Y-%m-%d %H:%M:%S")
                    if expiry_dt.timestamp() > time.time() + buffer_sec:
                        return data['access_token']
            except:
                pass
        return None

    def ensure_fresh_token(self, buffer_minutes=30):
        """Called by Scheduler: Refresh if expiring soon (< 30 min)"""
        token = self._read_token_from_file(buffer_sec=buffer_minutes * 60)
        if not token:
            print(f"🔄 Token expiring soon or missing. Pre-emptive refresh...")
            self.access_token = self._issue_token()

    def _issue_token(self):
        lock_path = self.token_file + ".lock"
        
        with open(lock_path, 'w') as lock_file:
            try:
                # 1. Acquire Exclusive Lock (Blocking)
                # This queues up other processes/threads so only ONE does the API call
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                
                # 2. Double-Check Strategy
                # Someone else might have refreshed it while we were waiting for lock
                existing = self._read_token_from_file(buffer_sec=60)
                if existing:
                    # print("  Token already refreshed by another process. Skipping.")
                    return existing

                # 3. Request New Token
                headers = {"content-type": "application/json"}
                body = {
                    "grant_type": "client_credentials",
                    "appkey": self.APP_KEY,
                    "appsecret": self.APP_SECRET
                }
                
                # Retry logic for Rate Limit
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        res = requests.post(f"{self.URL_BASE}/oauth2/tokenP", headers=headers, data=json.dumps(body), timeout=5)
                        
                        if res.status_code == 200:
                            data = res.json()
                            token = data['access_token']
                            expiry = data['access_token_token_expired']
                            
                            with open(self.token_file, 'w') as f:
                                json.dump({'access_token': token, 'expiry': expiry}, f)
                            
                            print(f"✅ Token Issued Successfully (Expires: {expiry})")
                            return token
                            
                        elif "EGW00133" in res.text: # Rate Limit Error
                            if attempt < max_retries - 1:
                                print(f"⚠️ Rate Limit Hit (EGW00133). Sleeping 65s before retry... ({attempt+1}/{max_retries})")
                                time.sleep(65) # Force clear 1-minute limit
                                continue
                            else:
                                print(f"❌ Token Issue Failed after retries: {res.text}")
                                return None
                        else:
                            print(f"❌ Token Issue Failed: {res.text}")
                            return None
                            
                    except Exception as e:
                        print(f"Token Issue Exception: {e}")
                        return None
                        
            finally:
                # Release Lock
                fcntl.flock(lock_file, fcntl.LOCK_UN)
        return None

    def get_price(self, symbol, exchange=None):
        """
        Get current price.
        If exchange is None, try NAS then NYS then AMS.
        Returns dictionary with 'price', 'diff', 'rate' or None.
        """
        if not self.access_token:
            self.access_token = self._issue_token()
            if not self.access_token: return None
            
        # [FIX] Prioritize 'NAS'/'AMS' but ensure iteration if failed.
        # If exchange is provided, try it first, then others if failed? 
        # Actually user logic in db.py passes exchange. KIS get_price tries specified list.
        # Let's ensure if exchange is passed, we ONLY try that? No, try others as fallback.
        # [Ver 5.7] KST Daytime Check (08:00 ~ 17:00)
        # Server timestamps might be UTC, so we convert explicitly
        utc_now = datetime.utcnow()
        kst_now = utc_now + timedelta(hours=9)
        is_daytime = 8 <= kst_now.hour < 17

        if not exchange:
            # Standard order + Daytime order
            if is_daytime:
                # Prioritize Daytime Exchanges
                search_order = ["BAQ", "BAY", "BAA", "NAS", "NYS", "AMS", "PAC"]
            else:
                search_order = ["NAS", "NYS", "AMS", "BAQ", "BAY", "PAC", "BAA"]
        else:
            # If specific exchange requested, also check its daytime counterpart
            daytime_map = {'NAS': 'BAQ', 'NYS': 'BAY', 'AMS': 'BAA'}
            search_order = [exchange]
            if exchange in daytime_map:
                if is_daytime:
                    # Prepend if daytime
                    search_order.insert(0, daytime_map[exchange])
                else:
                    search_order.append(daytime_map[exchange])
                
        best_result = None
        
        for excd in search_order:
            # print(f"  KIS API: Checking {excd} for {symbol}...") # Reduced logging
            res = self._fetch_price_request(excd, symbol)
            
            if res and res.get('rt_cd') == '0':
                out = res['output']
                if not out.get('last'): continue
                    
                try:
                    price = float(out['last'])
                    if price <= 0: continue
                    
                    data = {
                        'price': price,
                        'diff': float(out['diff']) if out.get('diff') else 0.0,
                        'rate': float(out['rate']) if out.get('rate') else 0.0,
                        'exchange': excd,
                        'tvol': float(out['tvol']) if out.get('tvol') else 0.0,
                        'high': float(out['high']) if out.get('high') else 0.0, # [NEW] Max Price for Trailing Stop
                    }
                    
                    # [Logic] Prefer data with Volume (Active Market)
                    # If we have no result, take this one.
                    # If we have a result with 0 volume, and this one has volume, take this one.
                    if best_result is None:
                        best_result = data
                    elif best_result['tvol'] == 0 and data['tvol'] > 0:
                        # print(f"  KIS API: Switching to Active Market {excd} (Vol: {data['tvol']})")
                        best_result = data
                        
                except (ValueError, TypeError):
                    continue
            
        if best_result:
             # print(f"  KIS API: Returning {symbol} from {best_result['exchange']} @ ${best_result['price']}")
             return best_result
             
        print(f"  KIS API: No valid price found for {symbol}")
        return None

    def _fetch_price_request(self, exchange, symbol):
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.APP_KEY,
            "appsecret": self.APP_SECRET,
            "tr_id": "HHDFS00000300"
        }
        params = {
            "AUTH": "",
            "EXCD": exchange,
            "SYMB": symbol
        }
        try:
            res = requests.get(f"{self.URL_BASE}/uapi/overseas-price/v1/quotations/price", headers=headers, params=params, timeout=1.5)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            # print(f"KIS API Request Error: {e}")
            pass
        return None

    def get_daily_price(self, symbol, exchange=None):
        """
        Get daily price history (Yesterday Close etc).
        Returns list of daily dictionaries.
        """
        if not exchange:
            exchange = get_exchange_code(symbol)
            
        return self._fetch_daily_price_request(exchange, symbol)

    def _fetch_daily_price_request(self, exchange, symbol):
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.APP_KEY,
            "appsecret": self.APP_SECRET,
            "tr_id": "HHDFS76240000"  # Overseas Stock Daily Price
        }
        params = {
            "AUTH": "",
            "EXCD": exchange,
            "SYMB": symbol,
            "GUBN": "0", # 0: Daily, 1: Weekly, 2: Monthly
            "BYMD": "",
            "MODP": "1" # 1: Adjusted Price
        }
        try:
            res = requests.get(f"{self.URL_BASE}/uapi/overseas-price/v1/quotations/dailyprice", headers=headers, params=params, timeout=1.5)
            if res.status_code == 200:
                data = res.json()
                if data['rt_cd'] == '0':
                    return data['output2'] # output2 usually contains the list
        except Exception as e:
            # print(f"KIS API Daily Request Error: {e}")
            pass
    def get_minute_candles(self, symbol, interval_min=30, exchange=None, next_key=""):
        """
        Get minute candle data.
        Returns list of candles.
        interval_min: 1, 3, 5, 10, 15, 30, 60, 120
        """
        if not exchange:
            exchange = get_exchange_code(symbol)
            
        return self._fetch_minute_candles_request(exchange, symbol, str(interval_min), next_key)

    def _fetch_minute_candles_request(self, exchange, symbol, interval, next_key=""):
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.APP_KEY,
            "appsecret": self.APP_SECRET,
            "tr_id": "HHDFS76950200"
        }
        
        # Current Time for End? KIS usually returns recent from now.
        import datetime
        now_str = datetime.datetime.now().strftime("%H%M%S") # Not used in param but good to know
        
        params = {
            "AUTH": "",
            "EXCD": exchange,
            "SYMB": symbol,
            "NMIN": interval, 
            "PINC": "1", # 1: Includes gap correction? or 0. Usually 1.
            "NEXT": next_key, # Next Key
            "NREC": "120", # Number of records (120 max)
            "KEYB": "" # Key value?
        }
        
        try:
            res = requests.get(f"{self.URL_BASE}/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice", headers=headers, params=params, timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                if data['rt_cd'] == '0':
                    return data['output2'] # output2 is the list
        except Exception as e:
            # print(f"KIS Minute Chart Error: {e}")
            pass
        return None

def get_exchange_code(ticker):
    """
    종목 코드로 거래소 추정
    
    Args:
        ticker: 종목 코드
    
    Returns:
        str: 거래소 코드 (NAS/NYS/AMS)
    """
    # 나스닥 주요 종목
    nasdaq_tickers = [
        'TSLA', 'GOOGL', 'GOOG', 'AAPL', 'MSFT', 'AMZN', 'META', 'NVDA',
        'IONQ', 'TQQQ', 'SQQQ', 'QQQ', 'PLTR', 'AMD', 'UFO'
    ]
    
    # 아멕스 ETF (SOXL, SOXS, UPRO 등 주요 ETF 포함)
    amex_tickers = ['TMF', 'TLT', 'GLD', 'SLV', 'AAAU', 'SOXL', 'SOXS', 'UPRO']
    
    if ticker in nasdaq_tickers:
        return 'NAS'
    elif ticker in amex_tickers:
        return 'AMS'
    else:
        # 기본값: 뉴욕증권거래소
        return 'NYS'

def get_current_price(ticker, exchange=None):
    """
    해외 주식 현재가 조회 (kis_client 래퍼)
    
    Args:
        ticker: 종목 코드
        exchange: 거래소 코드 (NAS/NYS/AMS), None이면 자동 감지
    
    Returns:
        dict: {'price': float, 'is_open': bool} 또는 None
    """
    if not exchange:
        exchange = get_exchange_code(ticker)
    
    result = kis_client.get_price(ticker, exchange)
    
    if result and result.get('price'):
        return {
            'price': result['price'],
            'is_open': True  # KIS API가 응답하면 개장 중
        }
    
    return None

def get_minute_candles(ticker, interval, exchange=None):
    """
    해외 주식 분봉 조회 Wrapper
    """
    if not exchange:
        exchange = get_exchange_code(ticker)
    return kis_client.get_minute_candles(ticker, interval, exchange)

# Final Singleton
kis_client = KisApi()
