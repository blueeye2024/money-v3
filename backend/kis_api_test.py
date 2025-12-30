import requests
import json
import time

# User provided keys
APP_KEY = "PS9q8I7TgXLRu2XNJj2GZnaqGU2Uy1CtDZpI"
APP_SECRET = "KSgC+E/xD+fvGhquv0DLXXKXf9jD4c4jOLZLWuLCp004H+vx9RSQbcPR3CGO0Ox3SHhCykiaDgmjYM0grzH2/j9rnVUGa9GqylNLEFxBq9dYtGhCe01pZ4hGqn4j/U5raqWkQBYWwtzT3Hy/VOZ8eKWooJgbyH5gGygZuUifV7uVnYfMPec="

# Base URL (Real)
URL_BASE = "https://openapi.koreainvestment.com:9443"

def get_access_token():
    """Get OAuth Token"""
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    path = "/oauth2/tokenP"
    url = f"{URL_BASE}{path}"
    
    print(f"Requesting Token from {url}...")
    res = requests.post(url, headers=headers, data=json.dumps(body))
    
    if res.status_code == 200:
        data = res.json()
        print("Token received!")
        return data['access_token']
    else:
        print(f"Token Error: {res.status_code} - {res.text}")
        return None

def get_current_price(token, exchange, symbol):
    """Get Overseas Price"""
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "HHDFS00000300" # Real-time Quotation
    }
    
    path = "/uapi/overseas-price/v1/quotations/price"
    url = f"{URL_BASE}{path}"
    
    params = {
        "AUTH": "",
        "EXCD": exchange, # NAS, NYS, AMS
        "SYMB": symbol
    }
    
    print(f"Fetching Price for {exchange}:{symbol}...")
    res = requests.get(url, headers=headers, params=params)
    
    if res.status_code == 200:
        print("Price Data Received:")
        print(json.dumps(res.json(), indent=2, ensure_ascii=False))
    else:
        print(f"Price Error: {res.status_code} - {res.text}")

if __name__ == "__main__":
    token = get_access_token()
    if token:
        # Test TSLA
        get_current_price(token, "NAS", "TSLA")
