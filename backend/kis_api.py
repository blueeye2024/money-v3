import requests
import json
import time
import os
from datetime import datetime

class KisApi:
    def __init__(self):
        self.APP_KEY = "PS9q8I7TgXLRu2XNJj2GZnaqGU2Uy1CtDZpI"
        self.APP_SECRET = "KSgC+E/xD+fvGhquv0DLXXKXf9jD4c4jOLZLWuLCp004H+vx9RSQbcPR3CGO0Ox3SHhCykiaDgmjYM0grzH2/j9rnVUGa9GqylNLEFxBq9dYtGhCe01pZ4hGqn4j/U5raqWkQBYWwtzT3Hy/VOZ8eKWooJgbyH5gGygZuUifV7uVnYfMPec="
        self.URL_BASE = "https://openapi.koreainvestment.com:9443"
        self.token_file = "kis_token.json"
        self.access_token = self._load_token()

    def _load_token(self):
        """Load token from file or request new one"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    # Check expiry (giving 1 min buffer)
                    if datetime.strptime(data['expiry'], "%Y-%m-%d %H:%M:%S").timestamp() > time.time() + 60:
                        return data['access_token']
            except:
                pass
        return self._issue_token()

    def _issue_token(self):
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.APP_KEY,
            "appsecret": self.APP_SECRET
        }
        try:
            res = requests.post(f"{self.URL_BASE}/oauth2/tokenP", headers=headers, data=json.dumps(body), timeout=5)
            if res.status_code == 200:
                data = res.json()
                token = data['access_token']
                expiry = data['access_token_token_expired'] # Format: 2022-08-30 18:00:00
                
                with open(self.token_file, 'w') as f:
                    json.dump({'access_token': token, 'expiry': expiry}, f)
                return token
            else:
                print(f"Token Issue Failed: {res.text}")
                return None
        except Exception as e:
            print(f"Token Issue Exception: {e}")
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
            
        exchanges = [exchange] if exchange else ["NAS", "NYS", "AMS"]
        
        for excd in exchanges:
            res = self._fetch_price_request(excd, symbol)
            if res and res.get('rt_cd') == '0':
                out = res['output']
                # If 'last' price is empty, it means this exchange has no data for this ticker. Try next.
                if not out.get('last'):
                    continue
                    
                try:
                    return {
                        'price': float(out['last']) if out.get('last') else 0.0,
                        'diff': float(out['diff']) if out.get('diff') else 0.0,
                        'rate': float(out['rate']) if out.get('rate') else 0.0,
                        'exchange': excd
                    }
                except (ValueError, TypeError):
                    continue
            
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
        return None

# Singleton instance
kis_client = KisApi()

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
