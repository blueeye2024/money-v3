
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import os
import time

# Global Cache for Historical Data
_DATA_CACHE = {
    "30m": None,
    "5m": None,
    "market": None,
    "last_fetch": 0
}


def get_score_interpretation(score, position_text=""):
    is_sell = "매도" in position_text or "하단" in position_text
    if score >= 80: return "🚨긴급 매도" if is_sell else "✨강력 매수"
    if score >= 70: return "📉매도" if is_sell else "🟢매수"
    if score >= 50: return "⚠경계" if is_sell else "🟡관망"
    return "📉조정" if is_sell else "⚪관망"

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
    "GOOGL": "Alphabet Inc. Class A",
    "XPON": "Expion360 Inc."
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
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    
    now_kst = now_utc.astimezone(kst)
    now_est = now_utc.astimezone(est)
    
    return {
        "kst": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
        "est": now_est.strftime("%m/%d %H:%M:%S"),
        "full_str": f"{now_kst.strftime('%Y-%m-%d %H:%M:%S')} KST (EST: {now_est.strftime('%m/%d %H:%M:%S')})"
    }

def fetch_data():
    global _DATA_CACHE
    
    # Check Cache (5 Minutes = 300 Seconds)
    if time.time() - _DATA_CACHE["last_fetch"] < 300 and _DATA_CACHE["30m"] is not None:
        # Return cached data
        return _DATA_CACHE["30m"], _DATA_CACHE["5m"], _DATA_CACHE["market"], None

    # Fetch 30m data (Main) for Stocks
    tickers_str = " ".join(TARGET_TICKERS)
    
    print("Fetching 30m data for Stocks (Fresh)...")
    # Hide progress to keep logs clean
    data_30m = yf.download(tickers_str, period="5d", interval="30m", prepost=True, group_by='ticker', threads=False, progress=False)
    
    print("Fetching 5m data for Stocks (Fresh)...")
    data_5m = yf.download(tickers_str, period="5d", interval="5m", prepost=True, group_by='ticker', threads=False, progress=False)
    
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
    
    # Update Cache
    _DATA_CACHE["30m"] = data_30m
    _DATA_CACHE["5m"] = data_5m
    _DATA_CACHE["market"] = market_data
    _DATA_CACHE["last_fetch"] = time.time()
    
    return data_30m, data_5m, market_data, None
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

def analyze_ticker(ticker, df_30mRaw, df_5mRaw, market_vol_score=0, is_held=False, real_time_info=None, holdings_data=None):
    # Retrieve Stock Name
    stock_name = TICKER_NAMES.get(ticker, ticker)
    
    try:
        # Match ticker using MultiIndex or Flat
        df_30 = None
        df_5 = None

        if isinstance(df_30mRaw.columns, pd.MultiIndex):
            if ticker in df_30mRaw.columns.levels[0]:
                df_30 = df_30mRaw[ticker].copy()
                df_30.dropna(subset=['Close'], inplace=True)
        elif ticker in df_30mRaw.columns:
             pass 

        if isinstance(df_5mRaw.columns, pd.MultiIndex):
            if ticker in df_5mRaw.columns.levels[0]:
                df_5 = df_5mRaw[ticker].copy()
                df_5.dropna(subset=['Close'], inplace=True)
        
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
        
        # Override with Real-time Info if available
        if real_time_info:
            current_price = float(real_time_info['price'])
            # rate is percentage change (e.g. +0.03 means 0.03%)
            change_pct = float(real_time_info['rate'])
            # Note: Indicator checks below (SMA, Cross) use df_30 (Candle Close). 
            # This is acceptable (Signals on close, Price on live).
            # But Box Breakout uses `current_price` variable, so it will be accurate.
        
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

        # Force Signal Time to Current Real-time Update (User Request)
        # Since we use Real-time Price and re-evaluate Breakout/Position,
        # we update the signal timestamp to reflect the latest analysis time.
        kst = pytz.timezone('Asia/Seoul')
        signal_time = datetime.now(kst)

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
            
            if current_price > box_high: position = "✨ 박스권 돌파 성공 (상단)"
            elif current_price < box_low: position = "✨ 박스권 돌파 성공 (하단)"
            
        # === User Holding Based Position Overlay ===
        # If Held: Buy/Hold/Observe -> "매수 유지", Sell -> "매도"
        # If Not Held: Buy -> "매수", Sell/Observe -> "미보유"
        
        algo_position = position # Save algo string for scoring?
        # Actually score depends on `is_buy_signal` derived from `position` text.
        # Refined Logic:
        # We need to construct a display string (`final_position`) AND ensure scoring logic uses the ALGO signal, not the display string?
        # User said "보유하고 있지 않은 종목은 ... 미보유라고 하면되". 
        # But for Scoring? "미보유" typically scores 0 (Base 20 if observes?).
        # If I change `position` string, downstream logic (`is_buy_signal`) changes.
        
        # Let's derive `is_buy_signal` etc. from `position` BEFORE overriding it for display?
        # But `analyze_ticker` returns `position` for display.
        # I should keep `position` as the final display string.
        # But calculate Scores based on technicals (Algo Position).
        # However, if I display "미보유", the Dashboard shouldn't show "Buy Score 80".
        # If "미보유" (Not Held & Sell/Observe), maybe score should reflect that?
        # User didn't specify Score changes for Holding status. "종목별 상세분석에서도 매수하고 있는 경우 매수 유지로 하고 ... " -> talking about Display.
        # But logic says "없는 종목의 경우 매수 신호가 나오면 매수".
        
        # Strategy:
        # 1. Calculate Technical Position (`tech_position`).
        # 2. Derive User Display Position (`user_position`) based on `is_held`.
        # 3. Use `tech_position` for Scoring? Or `user_position`?
        # If I have "미보유", it generally means "Do nothing".
        
        # Let's implement the User Rules for `position` string variable.
        
        tech_position = position
        
        if is_held:
            # Holding
            if "매도" in tech_position or "하단" in tech_position:
                 position = "🚨 매도"
            else:
                 # Buy, Buy Hold, Observe -> Maintain Buy
                 position = "🔵 매수 유지"
        else:
            # Not Holding
            if "매수" in tech_position or "상단" in tech_position:
                 position = "🚨 매수"
            else:
                 # Sell, Sell Hold, Observe -> Not Held
                 position = "미보유"

            
        # Format Time
        formatted_signal_time = "-"
        if signal_time != "":
            try:
                # Handle Timezone
                st_target = signal_time
                if st_target.tzinfo is None:
                    st_target = st_target.replace(tzinfo=pytz.utc)
                
                st_kst = st_target.astimezone(pytz.timezone('Asia/Seoul'))
                formatted_signal_time = f"{st_kst.strftime('%m/%d %H:%M')} KST"
            except:
                formatted_signal_time = str(signal_time)

        macd = float(df_30['MACD'].iloc[-1])
        signal = float(df_30['Signal'].iloc[-1])
        rsi_val = float(df_30['RSI'].iloc[-1])
        
        news_prob = 50
        if rsi_val > 60: news_prob += 10
        if rsi_val < 40: news_prob -= 10
        if recent_cross_type == 'gold': news_prob += 20
        if recent_cross_type == 'dead': news_prob -= 20
        news_prob = max(0, min(100, news_prob))
        
        # === Cheongan Scoring Engine (User Rules) ===
        base_score = 0
        trend_score = 0
        reliability_score = 0
        breakout_score = 0
        market_score = market_vol_score

        is_buy_signal = "매수" in position or "상단" in position
        is_sell_signal = "매도" in position or "하단" in position
        is_observing = "관망" in position

        # 1. Base Score
        if not is_observing:
            base_score = 50
        else:
            base_score = 20
        
        # Multi-Timeframe Logic
        t30 = 'UP' if last_sma10 > last_sma30 else 'DOWN'
        t5 = 'UP' if last_5m_sma10 > last_5m_sma30 else 'DOWN'
        
        if t30 == t5:
            base_score += 10
        else:
            base_score -= 10
            
        # Auxiliary Indicators (Max 20) - User Request
        aux_score = 0
        bb_mid = float(df_30['BB_Mid'].iloc[-1])
        
        # (1) RSI (+5)
        # Buy/Up: 45~75 (Healthy Momentum), Sell/Down: 25~55
        if is_buy_signal or (is_observing and t30=='UP'):
            if 45 <= rsi_val <= 75: aux_score += 5
        elif is_sell_signal or (is_observing and t30=='DOWN'):
            if 25 <= rsi_val <= 55: aux_score += 5
            
        # (2) MACD (+5)
        if is_buy_signal or (is_observing and t30=='UP'):
            if macd > signal: aux_score += 5
        elif is_sell_signal or (is_observing and t30=='DOWN'):
            if macd < signal: aux_score += 5
            
        # (3) Bollinger Trend (+5)
        if is_buy_signal or (is_observing and t30=='UP'):
            if current_price > bb_mid: aux_score += 5
        elif is_sell_signal or (is_observing and t30=='DOWN'):
            if current_price < bb_mid: aux_score += 5
            
        # (4) Cross Type Match (+5)
        if (is_buy_signal and recent_cross_type == 'gold') or \
           (is_sell_signal and recent_cross_type == 'dead'):
            aux_score += 5
            
        base_score += aux_score
        
        base_score = max(0, base_score)

        # Signal Price & Bars
        sig_price = current_price
        bars_since = 0
        if cross_idx < 0: # Valid cross index
            try:
                sig_price = df_30['Close'].iloc[cross_idx]
                bars_since = abs(cross_idx)
            except:
                pass
        
        # 2. Trend Score
        if is_buy_signal and current_price > sig_price:
            trend_score = 10
        elif is_sell_signal and current_price < sig_price:
            trend_score = 10
        
        # 3. Reliability Score
        if not is_observing and bars_since >= 2:
            raw_diff_pct = ((current_price - sig_price) / sig_price) * 100
            profit_rate = raw_diff_pct if is_buy_signal else -raw_diff_pct
            
            if 1.5 <= profit_rate < 3.0:
                reliability_score = 5
            elif 3.0 <= profit_rate < 5.0:
                reliability_score = 8
            elif profit_rate >= 5.0:
                reliability_score = 5
            elif -5.0 < profit_rate <= -3.0:
                reliability_score = -3
            elif profit_rate <= -5.0:
                reliability_score = -7

        # 4. Breakout Score
        if not is_observing and bars_since >= 2:
            recent_12h = df_30.iloc[-24:]
            # Exclude current bar to find previous high/low? 
            # Logic: "CurrentPrice >= High12h". 
            # Usually High12h implies the specific level established previously. 
            # Let's use max of recent 24 bars including current or excluding?
            # User said: "CurrentPrice >= High12h". If current breaks the High of the Window.
            # I will compare Current Close against Max High of previous 23 bars.
            prev_12h_high = recent_12h['High'].iloc[:-1].max()
            prev_12h_low = recent_12h['Low'].iloc[:-1].min()
            
            if is_buy_signal and current_price >= prev_12h_high:
                breakout_score = 10
            elif is_sell_signal and current_price <= prev_12h_low:
                breakout_score = 10

        # PnL Score Adjustment (Revised: Higher Score for Profit-Taking & Stop-Loss)
        pnl_impact = 0
        pnl_pct_held = 0.0
        if is_held and is_sell_signal and holdings_data and ticker in holdings_data and isinstance(holdings_data[ticker], dict):
             avg_price = holdings_data[ticker].get('avg_price', 0)
             if avg_price > 0:
                 pnl_pct_held = ((current_price - avg_price) / avg_price) * 100
                 if pnl_pct_held > 0:
                     # 수익 실현 (Lock-in): 1%당 +5점 가산
                     pnl_impact = pnl_pct_held * 5
                 else:
                     # 리스크 관리 (Stop-loss): 1%당 +10점 가산 (손절은 더 강력하게 권고)
                     pnl_impact = abs(pnl_pct_held) * 10

        # Technical Sell Proposal Boost (+10)
        # 만약 가격이 볼린저 밴드 하단을 건드리면 하락 가속화로 판단, 매도 점수 추가 가산
        if is_sell_signal:
            bb_low = float(df_30['BB_Lower'].iloc[-1])
            if current_price < bb_low:
                pnl_impact += 10

        # 6. Total Score
        final_score = base_score + trend_score + reliability_score + breakout_score + market_score + pnl_impact
        final_score = int(max(0, min(100, final_score)))
        
        score_details = {
            "base": base_score,
            "trend": trend_score,
            "reliability": reliability_score,
            "breakout": breakout_score,
            "market": market_score,
            "pnl_adj": round(pnl_impact, 1),
            "total": final_score
        }

        # Change Pct (Only use historical fallback if Real-time info is missing)
        if not real_time_info:
            prev_close = df_30['Close'].iloc[-2] # Default fallback
            try:
                current_date = df_30.index[-1].date()
                prev_day_data = df_30[df_30.index.date < current_date]
                if not prev_day_data.empty:
                    prev_close = prev_day_data['Close'].iloc[-1]
                    change_pct = ((current_price - prev_close) / prev_close) * 100
            except:
                 pass

        # Generate Stock Specific Mock News (Technical)
        stock_news = []
        if recent_cross_type == 'gold': stock_news.append("골든크로스 발생: 강력한 매수 신호 포착")
        if recent_cross_type == 'dead': stock_news.append("데드크로스 발생: 매도 압력 증가")
        if is_box: stock_news.append("박스권 횡보 지속: 돌파 여부 모니터링 필요")
        if rsi_val > 70: stock_news.append("RSI 과매수권 진입: 차익 실현 매물 주의")
        elif rsi_val < 30: stock_news.append("RSI 과매도권 진입: 기술적 반등 기대감 유효")
        if change_pct > 3.0: stock_news.append(f"급등세 연출: 전일 대비 {change_pct:.1f}% 상승")
        elif change_pct < -3.0: stock_news.append(f"급락세 연출: 전일 대비 {abs(change_pct):.1f}% 하락")
        
        # Limit to 2
        if pnl_adjustment != 0:
            direction = "차감" if pnl_adjustment > 0 else "가점"
            stock_news.append(f"보유 수익률({pnl_pct_held:.1f}%) 반영: 점수 {abs(int(pnl_adjustment))}점 {direction}")
            
        # Limit to 2 (Prioritize PnL msg if exists)
        stock_news = stock_news[:2]
        if not stock_news: stock_news.append("특이사항 없음: 일반적인 시장 흐름 추종")

        result = {
            "ticker": ticker,
            "name": stock_name,
            "current_price": float(current_price) if pd.notnull(current_price) else None,
            "change_pct": float(change_pct) if pd.notnull(change_pct) else 0.0,
            "position": position,
            "last_cross_type": recent_cross_type,
            "signal_time": formatted_signal_time,
            "signal_time_raw": str(signal_time) if signal_time != "" else None, 
            "is_box": bool(is_box),
            "box_high": float(box_high) if pd.notnull(box_high) else 0.0,
            "box_low": float(box_low) if pd.notnull(box_low) else 0.0,
            "rsi": float(rsi_val) if pd.notnull(rsi_val) else None,
            "macd": float(macd) if pd.notnull(macd) else None,
            "macd_sig": float(signal) if pd.notnull(signal) else None,
            "prob_up": float(news_prob),
            "score": final_score,
            "score_interpretation": get_score_interpretation(final_score, position),
            "score_details": score_details,
            "news_items": stock_news,
            "is_held": is_held
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

def run_analysis(held_tickers=[]):
    data_30m, data_5m, market_data, _ = fetch_data()
    # Calculate Market Volatility Score
    market_vol_score = -5 # Default: Neutral/Flat (Bad? User says High Volatility is Good (+5))
    # User: "보합/혼조세면 -5점 , 강한 상승장이나 하락장이면 +5점"
    
    if "S&P500" in market_data:
        df_spy = market_data["S&P500"]
        if not df_spy.empty and len(df_spy) >= 2:
            # Check 1 day change
            curr = df_spy['Close'].iloc[-1]
            prev = df_spy['Close'].iloc[-2]
            spy_change = ((curr - prev) / prev) * 100
            
            if abs(spy_change) >= 0.5:
                market_vol_score = 5
    
    # Fetch Real-time Prices (KIS)
    from kis_api import kis_client
    from concurrent.futures import ThreadPoolExecutor

    real_time_map = {}
    try:
        # Exchange Mapping for Speed (Avoid 3 sequential requests)
        EXCHANGE_MAP_KIS = {
            "TSLA": "NAS", "GOOGL": "NAS", "AMZU": "NAS", "UFO": "NAS", "NVDA": "NAS", "AAPL": "NAS", "MSFT": "NAS", "AMZN": "NAS", "NFLX": "NAS", "AMD": "NAS", "INTC": "NAS", "QQQ": "NAS", "TQQQ": "NAS", "SQQQ": "NAS", "XPON": "NAS",
            "SOXL": "NYS", "SOXS": "NYS", "UPRO": "NYS", "AAAU": "NYS", "IONQ": "NYS", "SPY": "NYS", "IVV": "NYS", "VOO": "NYS"
        }
        
        def fetch_wrapper(t):
             excd = EXCHANGE_MAP_KIS.get(t)
             return t, kis_client.get_price(t, exchange=excd)
        
        # Increase workers slightly as we have fast timeout
        with ThreadPoolExecutor(max_workers=8) as executor:
             futs = [executor.submit(fetch_wrapper, t) for t in TARGET_TICKERS]
             # Add total timeout for entire batch to prevent hanging
             # We rely on individual timeouts (1.5s)
             for f in futs:
                 try:
                     t, info = f.result(timeout=4) # Max wait per task
                     if info: real_time_map[t] = info
                 except: pass

    except Exception as e:
        print(f"KIS Price Fetch Error: {e}")

    results = []
    
    for ticker in TARGET_TICKERS:
        is_held = ticker in held_tickers
        rt_info = real_time_map.get(ticker)
        # held_tickers is the dict from db.get_current_holdings
        res = analyze_ticker(ticker, data_30m, data_5m, market_vol_score, is_held, real_time_info=rt_info, holdings_data=held_tickers)
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
