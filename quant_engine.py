import pandas as pd
import numpy as np

try:
    from news_engine import fetch_stock_news_sentiment
except ImportError:
    def fetch_stock_news_sentiment(symbol):
        return {"sentiment": "NEUTRAL", "score": 0, "headlines": []}

def add_indicators(df):
    """तांत्रिक इंडिकेटर्स (EMA, VWAP, RSI, ATR)"""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or len(df) < 10:
        return df
    
    df = df.copy()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
    
    v = df['Volume'].replace(0, 1)
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = (tp * v).cumsum() / v.cumsum()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = df['RSI'].fillna(50)
    
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['ATR'] = true_range.rolling(14).mean()
    
    return df

def analyze_index(symbol, df_15m, display_name=None):
    """NIFTY / BANKNIFTY Options (CALL / PUT) साठी टेलिग्राम सुसंगत अनालिसिस"""
    if df_15m is None or not isinstance(df_15m, pd.DataFrame) or df_15m.empty or len(df_15m) < 10:
        return None
    
    name = display_name if display_name else symbol
    df_15m = add_indicators(df_15m)
    l = df_15m.iloc[-1]
    price = float(l["Close"])
    
    raw_atr = l["ATR"] if pd.notna(l["ATR"]) else 0
    atr = max(float(raw_atr), price * 0.004)
    
    vwap = float(l["VWAP"]) if pd.notna(l["VWAP"]) else price
    rsi = float(l["RSI"]) if pd.notna(l["RSI"]) else 50
    
    if price >= vwap and rsi >= 48:
        action = "BUY CALL (CE)"
        sl = round(price - (1.0 * atr), 2)
        tp = round(price + (1.8 * atr), 2)
        bias = "BULLISH"
    else:
        action = "BUY PUT (PE)"
        sl = round(price + (1.0 * atr), 2)
        tp = round(price - (1.8 * atr), 2)
        bias = "BEARISH"
        
    return {
        "name": name,
        "symbol": symbol,
        "price": round(price, 2),
        "action": action,
        "entry": round(price, 2),
        "sl": sl,
        "tp": tp,
        "rsi": round(rsi, 1),
        "bias": bias,
        "confidence": 85
    }

def build_scanner_row(symbol, df_15m, df_daily=None, *args, **kwargs):
    """360-Degree Deep AI Research for Equity Stocks"""
    if df_15m is None or not isinstance(df_15m, pd.DataFrame) or df_15m.empty or len(df_15m) < 10:
        return None

    sector = kwargs.get("sector", "EQUITY")
    df_15m = add_indicators(df_15m)
    l = df_15m.iloc[-1]
    price = float(l["Close"])
    
    raw_atr = l["ATR"] if pd.notna(l["ATR"]) else 0
    atr = max(float(raw_atr), price * 0.005)

    daily_trend = "BULLISH"
    if df_daily is not None and isinstance(df_daily, pd.DataFrame) and not df_daily.empty and len(df_daily) >= 15:
        df_daily_ind = add_indicators(df_daily)
        if df_daily_ind.iloc[-1]["Close"] < df_daily_ind.iloc[-1]["EMA_50"]:
            daily_trend = "BEARISH"

    news_res = fetch_stock_news_sentiment(symbol)
    
    reasons = []
    bull_score = 50
    bear_score = 50

    if daily_trend == "BULLISH":
        bull_score += 15
        reasons.append("Daily Macro Trend: बुलिश ट्रॅजेक्टरी (Above Daily EMA 50)")
    else:
        bear_score += 15
        reasons.append("Daily Macro Trend: बेअरिश ट्रॅजेक्टरी (Below Daily EMA 50)")

    if price > l["VWAP"]:
        bull_score += 15
        reasons.append("Smart Money Flow: Price VWAP च्या वर (Institutional Buying)")
    else:
        bear_score += 15
        reasons.append("Smart Money Flow: Price VWAP च्या खाली (Institutional Selling)")

    vol_curr = float(l["Volume"]) if pd.notna(l["Volume"]) else 0
    vol_avg = float(l["Vol_SMA20"]) if pd.notna(l["Vol_SMA20"]) else 1
    if vol_curr > (1.2 * vol_avg):
        if bull_score > bear_score: bull_score += 10
        else: bear_score += 10
        reasons.append(f"Volume Spike: 20-SMA पेक्षा {round(vol_curr/vol_avg, 1)}x पटीने जास्त व्हॉल्यूम")

    if news_res['sentiment'] == "BULLISH":
        bull_score += 10
        reasons.append("24/7 Live News: मार्केट बातम्यांचा पॉझिटिव्ह पाठिंबा")
    elif news_res['sentiment'] == "BEARISH":
        bear_score += 10
        reasons.append("24/7 Live News: मार्केट बातम्यांचा निगेटिव्ह प्रभाव")

    rsi = float(l["RSI"]) if pd.notna(l["RSI"]) else 50
    reasons.append(f"RSI Indicator: Current Index {round(rsi, 1)}")

    if bull_score >= bear_score:
        action = "BUY / CALL"
        sl = round(price - (1.0 * atr), 2)
        tp1 = round(price + (1.2 * atr), 2)
        tp2 = round(price + (2.2 * atr), 2)
        confidence = min(bull_score, 98)
    else:
        action = "SELL / PUT"
        sl = round(price + (1.0 * atr), 2)
        tp1 = round(price - (1.2 * atr), 2)
        tp2 = round(price - (2.2 * atr), 2)
        confidence = min(bear_score, 98)

    return {
        "name": symbol,
        "symbol": symbol, "sector": sector, "price": round(price, 2),
        "action": action, "confidence": confidence, "entry": round(price, 2),
        "sl": sl, "tp1": tp1, "tp2": tp2, "reasons": reasons
    }