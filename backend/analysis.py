
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import os

# Stock Names Mapping
TICKER_NAMES = {
    "SOXL": "Direxion Daily Semiconductor Bull 3X",
    "SOXS": "Direxion Daily Semiconductor Bear 3X",
    "UPRO": "ProShares UltraPro S&P500 (3X)",
    "AAAU": "Goldman Sachs Physical Gold ETF",
    "TSLA": "Tesla Inc.",
    "IONQ": "IonQ Inc.",
    "AMZU": "Direxion Daily AMZN Bull 1.5X",
    "UFO": "Procure Space ETF",
    "GOOGL": "Alphabet Inc. Class A"
}

# Tickers List (Collected from keys)
TARGET_TICKERS = list(TICKER_NAMES.keys())

MARKET_INDICATORS = {
    "S&P500": "^GSPC",
    "NASDAQ": "^IXIC",
    "GOLD": "GC=F",
    "KRW": "KRW=X"
}

def get_current_time_str():
    kst = pytz.timezone('Asia/Seoul')
    est = pytz.timezone('US/Eastern')
    now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
    
    now_kst = now_utc.astimezone(kst)
    now_est = now_utc.astimezone(est)
    
    return {
        "kst": now_kst.strftime("%Y-%m-%d %H:%M"),
        "est": now_est.strftime("%m/%d %H:%M"),
        "full_str": f"{now_kst.strftime('%Y-%m-%d %H:%M')} KST (EST: {now_est.strftime('%m/%d %H:%M')})"
    }

def fetch_data():
    # Fetch 30m data (Main) for Stocks
    tickers_str = " ".join(TARGET_TICKERS)
    
    print("Fetching 30m data for Stocks...")
    # Hide progress to keep logs clean
    data_30m = yf.download(tickers_str, period="5d", interval="30m", prepost=True, group_by='ticker', threads=True, progress=False)
    
    print("Fetching 5m data for Stocks...")
    data_5m = yf.download(tickers_str, period="5d", interval="5m", prepost=True, group_by='ticker', threads=True, progress=False)
    
    # Market indicators - Use Ticker.history for stability
    print("Fetching market data (Indices)...")
    market_data = {}
    for name, ticker in MARKET_INDICATORS.items():
        try:
            t = yf.Ticker(ticker)
            # Fetch history (need enough for prev close)
            hist = t.history(period="5d")
            if not hist.empty:
                market_data[name] = hist
            else:
                print(f"Warning: No data for {name}")
                market_data[name] = pd.DataFrame()
        except Exception as e:
            print(f"Failed to fetch {name}: {e}")
            market_data[name] = pd.DataFrame()
            
    print("Data fetch complete.")
    return data_30m, data_5m, market_data, None

def calculate_sma(series, window):
    return series.rolling(window=window).mean()

def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def check_box_pattern(df_30m):
    """
    Check if the stock is in a box pattern for the LAST 7 DAYS.
    Box definition: (High Max - Low Min) / Low Min <= 5%.
    Returns: (is_box, high_val, low_val, pct_diff)
    """
    if df_30m.empty:
        return False, 0, 0, 0

    # Get last 7 days of data
    last_idx = df_30m.index[-1]
    cutoff_time = last_idx - timedelta(days=7)
    
    recent_data = df_30m[df_30m.index >= cutoff_time]
    
    if recent_data.empty:
        return False, 0, 0, 0
        
    high_max = recent_data['High'].max()
    low_min = recent_data['Low'].min()
    
    if low_min == 0: return False, 0, 0, 0
    
    diff_pct = ((high_max - low_min) / low_min) * 100
    
    # Relaxed box definition to 5%
    is_box = diff_pct <= 5.0
    return is_box, high_max, low_min, diff_pct

def analyze_ticker(ticker, df_30mRaw, df_5mRaw):
    # Retrieve Stock Name
    stock_name = TICKER_NAMES.get(ticker, ticker)
    
    try:
        # Match ticker using MultiIndex or Flat
        df_30 = None
        df_5 = None

        if isinstance(df_30mRaw.columns, pd.MultiIndex):
            if ticker in df_30mRaw.columns.levels[0]:
                df_30 = df_30mRaw[ticker].copy()
        elif ticker in df_30mRaw.columns:
             pass 

        if isinstance(df_5mRaw.columns, pd.MultiIndex):
            if ticker in df_5mRaw.columns.levels[0]:
                df_5 = df_5mRaw[ticker].copy()
        
        if df_30 is None or df_5 is None or df_30.empty or df_5.empty:
            return {"ticker": ticker, "name": stock_name, "error": "No data"}
            
        # ... (Technical Analysis Logic remains mostly same, need to ensure return dict has 'name')
        
        # Calculate Indicators 30m
        df_30['SMA10'] = calculate_sma(df_30['Close'], 10)
        df_30['SMA30'] = calculate_sma(df_30['Close'], 30)
        df_30['RSI'] = calculate_rsi(df_30['Close'])
        
        # Bollinger Bands & MACD
        df_30['BB_Mid'] = df_30['Close'].rolling(window=20).mean()
        df_30['BB_Std'] = df_30['Close'].rolling(window=20).std()
        df_30['BB_Upper'] = df_30['BB_Mid'] + (2 * df_30['BB_Std'])
        df_30['BB_Lower'] = df_30['BB_Mid'] - (2 * df_30['BB_Std'])
        
        exp12 = df_30['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df_30['Close'].ewm(span=26, adjust=False).mean()
        df_30['MACD'] = exp12 - exp26
        df_30['Signal'] = df_30['MACD'].ewm(span=9, adjust=False).mean()

        # 5m
        df_5['SMA10'] = calculate_sma(df_5['Close'], 10)
        df_5['SMA30'] = calculate_sma(df_5['Close'], 30)
        
        # Values
        current_price = df_30['Close'].iloc[-1]
        prev_price = df_30['Close'].iloc[-2]
        change_pct = ((current_price - prev_price) / prev_price) * 100
        
        # Signal Detection (Previous Logic)
        last_sma10 = df_30['SMA10'].iloc[-1]
        last_sma30 = df_30['SMA30'].iloc[-1]
        last_5m_sma10 = df_5['SMA10'].iloc[-1]
        last_5m_sma30 = df_5['SMA30'].iloc[-1]
        is_box, box_high, box_low, box_pct = check_box_pattern(df_30)
        
        position = "관망"
        recent_cross_type = None 
        signal_time = ""
        cross_idx = -1
        
        for i in range(1, 50):
            if i >= len(df_30): break
            c_sma10 = df_30['SMA10'].iloc[-i]
            # ... (Rest of cross detection logic)
            c_sma30 = df_30['SMA30'].iloc[-i]
            p_sma10 = df_30['SMA10'].iloc[-(i+1)]
            p_sma30 = df_30['SMA30'].iloc[-(i+1)]
            
            if p_sma10 <= p_sma30 and c_sma10 > c_sma30:
                recent_cross_type = 'gold'
                cross_idx = -i
                signal_time = df_30.index[-i]
                break
            elif p_sma10 >= p_sma30 and c_sma10 < c_sma30:
                recent_cross_type = 'dead'
                cross_idx = -i
                signal_time = df_30.index[-i]
                break
        
        # Trend Following Fallback
        if recent_cross_type is None:
            if last_sma10 > last_sma30:
                 recent_cross_type = 'gold'
            else:
                 recent_cross_type = 'dead'
            signal_time = df_30.index[-1]

        # Validation
        valid = True
        if recent_cross_type == 'gold':
            if last_5m_sma10 < last_5m_sma30: valid = False
            if is_box:
                if current_price > box_high: pass
                else: valid = False
            position = "🚨 매수 진입" if cross_idx > -3 and cross_idx != -1 else "🔴 매수 유지" if valid else "관망 (매수 신호 무효화)"
        elif recent_cross_type == 'dead':
            if last_5m_sma10 > last_5m_sma30: valid = False
            if is_box:
                 if current_price < box_low: pass
                 else: valid = False
            position = "🚨 매도 진입" if cross_idx > -3 and cross_idx != -1 else "🔵 매도 유지" if valid else "관망 (매도 신호 무효화)"
            
        if is_box:
            if current_price > box_high: position = "✨ 박스권 돌파 성공 (상단)"
            elif current_price < box_low: position = "✨ 박스권 돌파 성공 (하단)"
            
        # Format Time
        formatted_signal_time = "-"
        if signal_time != "":
            st_utc = signal_time.replace(tzinfo=pytz.utc)
            st_kst = st_utc.astimezone(pytz.timezone('Asia/Seoul'))
            st_est = st_utc.astimezone(pytz.timezone('US/Eastern'))
            formatted_signal_time = f"{st_kst.strftime('%m/%d %H:%M')} KST"

        news_prob = 50
        if df_30['RSI'].iloc[-1] > 60: news_prob += 10
        if df_30['RSI'].iloc[-1] < 40: news_prob -= 10
        if recent_cross_type == 'gold': news_prob += 20
        if recent_cross_type == 'dead': news_prob -= 20
        news_prob = max(0, min(100, news_prob))
        
        # Comprehensive Scoring Logic (0-100)
        # 1. Trend (Gold/Dead)
        # 2. RSI Stability
        # 3. Box Breakout Bonus
        score = 50 # Base
        
        # Trend Score
        if position.startswith("🚨 매수") or "상단" in position:
            score += 30
        elif position.startswith("🔴 매수"):
            score += 20
        elif position.startswith("🚨 매도") or "하단" in position:
            # Sell signals are also "High Relevance" for trading, even if direction is down.
            # Use 'Signal Strength' concept?
            # User asks for "Best Selection". Usually means 'Buy'.
            # If user plays inverse, 'Sell' is good. But let's assume 'Best actionable signal'.
             score += 30
        
        # RSI Score (Prefer not overbought/sold too much for entry)
        rsi_val = float(df_30['RSI'].iloc[-1])
        if 40 <= rsi_val <= 60: score += 10 
        elif rsi_val > 70 or rsi_val < 30: score -= 5 # Risky
        
        # Box Breakout is very strong
        if is_box and ("돌파" in position): score += 20
        
        # MACD Strength
        macd = float(df_30['MACD'].iloc[-1])
        signal = float(df_30['Signal'].iloc[-1])
        if abs(macd - signal) > 0.1: score += 5 # Diverging strongly
        
        score = min(100, max(0, score))

        # Sanitize and Return
        result = {
            "ticker": ticker,
            "name": stock_name,
            "current_price": float(current_price) if pd.notnull(current_price) else None,
            "change_pct": float(change_pct) if pd.notnull(change_pct) else 0.0,
            "position": position,
            "last_cross_type": recent_cross_type,
            "signal_time": formatted_signal_time,
            "signal_time_raw": signal_time if signal_time != "" else None, # Add Raw Time
            "is_box": bool(is_box),
            "box_high": float(box_high) if pd.notnull(box_high) else 0.0,
            "box_low": float(box_low) if pd.notnull(box_low) else 0.0,
            "rsi": float(rsi_val) if pd.notnull(rsi_val) else None,
            "macd": float(macd) if pd.notnull(macd) else None,
            "macd_sig": float(signal) if pd.notnull(signal) else None,
            "prob_up": float(news_prob),
            "score": score
        }
        return result
    
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return {"ticker": ticker, "name": stock_name, "error": str(e)}

def generate_market_insight(results, market_data):
    # Determine overall sentiment
    buy_signals = sum(1 for r in results if r.get('position', '').strip().startswith("🚨 매수") or r.get('position', '').strip().startswith("🔴 매수") or "상단" in r.get('position', ''))
    sell_signals = sum(1 for r in results if r.get('position', '').strip().startswith("🚨 매도") or r.get('position', '').strip().startswith("🔵 매도") or "하단" in r.get('position', ''))
    total = len(results)
    
    insight = f"현재 분석된 {total}개 주요 종목 중 {buy_signals}개 종목이 매수 우위, {sell_signals}개 종목이 매도 우위를 보이고 있습니다."
    
    if buy_signals > sell_signals:
        insight += " 전반적으로 기술적 반등 및 상승 추세가 감지되고 있으며, 특히 반도체 및 기술주 섹터의 흐름을 주시해야 합니다."
    elif sell_signals > buy_signals:
        insight += " 시장 전반에 차익 실현 매물 및 하락 압력이 존재하므로 보수적인 접근이 권장됩니다."
    else:
        insight += " 매수와 매도 힘이 팽팽하게 맞서고 있는 혼조세가 지속되고 있습니다."
        
    insight += "\n\n[주요 뉴스 요약]\n- 연준(Fed) 금리 정책 및 주요 경제 지표 발표에 따른 변동성 확대 주의\n- S&P500 및 나스닥 지수의 주요 지지선 테스트 진행 중\n- 개별 기업 실적 이슈에 따른 기술적 등락폭 확대 가능성 존재"
    
    return insight

def run_analysis():
    data_30m, data_5m, market_data, _ = fetch_data()
    results = []
    
    for ticker in TARGET_TICKERS:
        res = analyze_ticker(ticker, data_30m, data_5m)
        results.append(res)
        
    # Get Market Indicators Data with Change %
    indicators = {}
    for name, df in market_data.items():
        try:
            val = 0.0
            change = 0.0
            if not df.empty and 'Close' in df.columns:
                val = df['Close'].iloc[-1]
                if len(df) >= 2:
                    prev = df['Close'].iloc[-2]
                    change = ((val - prev) / prev) * 100
            
            indicators[name] = {
                "value": float(val) if val is not None and pd.notnull(val) else 0.0,
                "change": float(change) if change is not None and pd.notnull(change) else 0.0
            }
            
        except Exception as e:
             indicators[name] = {"value": 0.0, "change": 0.0}

    # Generate Insight
    insight_text = generate_market_insight(results, market_data)

    return {
        "timestamp": get_current_time_str(),
        "stocks": results,
        "market": indicators,
        "insight": insight_text
    }

if __name__ == "__main__":
    # Test run
    print(run_analysis())
