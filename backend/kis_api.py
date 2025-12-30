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
        res = requests.post(f"{self.URL_BASE}/oauth2/tokenP", headers=headers, data=json.dumps(body))
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
                return {
                    'price': float(out['last']),
                    'diff': float(out['diff']),
                    'rate': float(out['rate']),
                    'exchange': excd
                }
            time.sleep(0.05) # Rate limit safety
            
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
            res = requests.get(f"{self.URL_BASE}/uapi/overseas-price/v1/quotations/price", headers=headers, params=params, timeout=5)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            print(f"KIS API Request Error: {e}")
        return None

# Singleton instance
kis_client = KisApi()
