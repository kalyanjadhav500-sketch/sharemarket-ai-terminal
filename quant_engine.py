import pandas as pd
import numpy as np
from news_engine import fetch_stock_news_sentiment

def add_indicators(df):
    """तांत्रिक इंडिकेटर्स (EMA, VWAP, RSI, ATR, MACD, Volume)"""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or len(df) < 15:
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

def market_regime(df):
    default_res = {"regime": "NEUTRAL", "confidence": 50, "score": 50, "bull": 50, "bear": 50}
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or len(df) < 20:
        return default_res
    
    df = add_indicators(df)
    l = df.iloc[-1]
    bull = 0
    bear = 0
    if l['Close'] > l['EMA_21']: bull += 30
    else: bear += 30
    if l['Close'] > l['VWAP']: bull += 25
    else: bear += 25
    if l['RSI'] > 55: bull += 25
    elif l['RSI'] < 45: bear += 25
    
    reg_str = "BULLISH" if bull > bear else ("BEARISH" if bear > bull else "NEUTRAL")
    score = max(bull, bear)
    return {"regime": reg_str, "confidence": score, "score": score, "bull": bull, "bear": bear}

def sector_strength(sector_data=None):
    return {"BANKING": "BULLISH", "IT": "BULLISH", "AUTO": "NEUTRAL"}

def build_scanner_row(symbol, df_15m, df_daily=None, *args, **kwargs):
    """तांत्रिक + बातमी + व्हॉल्यूम ३६० डिग्री ऑल-इन-वन रिसर्च"""
    if df_15m is None or not isinstance(df_15m, pd.DataFrame) or df_15m.empty or len(df_15m) < 20:
        return None

    sector = kwargs.get("sector", "EQUITY")
    df_15m = add_indicators(df_15m)
    l = df_15m.iloc[-1]
    price = float(l["Close"])
    
    raw_atr = l["ATR"] if pd.notna(l["ATR"]) else 0
    atr = max(float(raw_atr), price * 0.006)

    # १. डेली चार्ट मॅक्रो ट्रेंड
    daily_trend = "BULLISH"
    if df_daily is not None and isinstance(df_daily, pd.DataFrame) and not df_daily.empty and len(df_daily) >= 20:
        df_daily_ind = add_indicators(df_daily)
        if df_daily_ind.iloc[-1]["Close"] < df_daily_ind.iloc[-1]["EMA_50"]:
            daily_trend = "BEARISH"

    # २. लाइव्ह न्यूज सेंटीमेंट स्कॅन
    news_res = fetch_stock_news_sentiment(symbol)
    
    reasons = []
    bull_score = 0
    bear_score = 0

    # ट्रेंड पॉईंट्स
    if daily_trend == "BULLISH":
        bull_score += 25
        reasons.append("Daily Macro Trend: अपट्रेंड (Daily EMA 50)")
    else:
        bear_score += 25
        reasons.append("Daily Macro Trend: डाउनट्रेंड (Daily EMA 50)")

    # स्मार्ट मनी प्रवाह (VWAP)
    if price > l["VWAP"]:
        bull_score += 20
        reasons.append("Smart Money Flow: Price VWAP च्या वर (Buyers Active)")
    else:
        bear_score += 20
        reasons.append("Smart Money Flow: Price VWAP च्या खाली (Sellers Active)")

    # व्हॉल्यूम स्पाइक फाईंड आउट
    vol_curr = float(l["Volume"]) if pd.notna(l["Volume"]) else 0
    vol_avg = float(l["Vol_SMA20"]) if pd.notna(l["Vol_SMA20"]) else 1
    if vol_curr > (1.3 * vol_avg):
        if bull_score > bear_score: bull_score += 15
        else: bear_score += 15
        reasons.append(f"Volume Analysis: 20-SMA पेक्षा {round(vol_curr/vol_avg, 1)}x जास्त व्हॉल्यूम")

    # न्यूज सेंटीमेंट फॅक्टर
    if news_res['sentiment'] == "BULLISH":
        bull_score += 15
        reasons.append("24/7 Live News: पॉझिटिव्ह सेंटीमेंट आणि हेडलाईन्स")
    elif news_res['sentiment'] == "BEARISH":
        bear_score += 15
        reasons.append("24/7 Live News: निगेटिव्ह बातमीचा प्रभाव")

    # RSI मोमेंटम
    rsi = float(l["RSI"])
    if 55 <= rsi <= 68:
        bull_score += 20
        reasons.append(f"RSI Momentum: स्ट्रॉंग झोन ({round(rsi,1)})")
    elif 32 <= rsi <= 45:
        bear_score += 20
        reasons.append(f"RSI Momentum: डाऊनवर्ड प्रेशर ({round(rsi,1)})")
    elif rsi > 70 or rsi < 30:
        return None  # ट्रेप झोनमध्ये नो ट्रेड!

    # अंतिम हाय-कॉन्व्हिक्शन फिल्टर (किमान ७०% स्कोर आवश्यक)
    if bull_score >= 70 and daily_trend == "BULLISH" and news_res['sentiment'] != "BEARISH":
        action = "BUY"
        sl = round(price - (1.0 * atr), 2)
        tp1 = round(price + (1.5 * atr), 2)
        tp2 = round(price + (2.5 * atr), 2)
        confidence = min(bull_score, 95)
    elif bear_score >= 70 and daily_trend == "BEARISH" and news_res['sentiment'] != "BULLISH":
        action = "SELL"
        sl = round(price + (1.0 * atr), 2)
        tp1 = round(price - (1.5 * atr), 2)
        tp2 = round(price - (2.5 * atr), 2)
        confidence = min(bear_score, 95)
    else:
        return None

    return {
        "symbol": symbol, "sector": sector, "price": round(price, 2),
        "action": action, "confidence": confidence, "entry": round(price, 2),
        "sl": sl, "tp1": tp1, "tp2": tp2, "qty": 1, "reasons": reasons
    }