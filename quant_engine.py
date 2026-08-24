import pandas as pd
import numpy as np

def add_indicators(df):
    """तांत्रिक इंडिकेटर्स जोडणे (EMA, VWAP, RSI, ATR, MACD)"""
    if df.empty or len(df) < 15:
        return df
    
    df = df.copy()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    # VWAP Calculation
    v = df['Volume'].replace(0, 1)
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = (tp * v).cumsum() / v.cumsum()
    
    # RSI Calculation
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = df['RSI'].fillna(50)
    
    # ATR Calculation
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['ATR'] = true_range.rolling(14).mean()
    
    # MACD Calculation
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['SIGNAL'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_HIST'] = df['MACD'] - df['SIGNAL']
    
    return df

def market_regime(df):
    """Streamlit Dashboard साठी Market Regime"""
    if df.empty or len(df) < 20:
        return "NEUTRAL", 50
    df = add_indicators(df)
    l = df.iloc[-1]
    if l['Close'] > l['EMA_50'] and l['RSI'] > 55:
        return "BULLISH", 80
    elif l['Close'] < l['EMA_50'] and l['RSI'] < 45:
        return "BEARISH", 80
    return "SIDEWAYS / NEUTRAL", 50

def sector_strength(sector_data=None):
    """Streamlit Dashboard साठी Sector Strength"""
    return {"BANKING": "BULLISH", "IT": "BULLISH", "AUTO": "NEUTRAL"}

def analyze_index(symbol, df, name):
    """NIFTY, BANK NIFTY, SENSEX इंडेक्स सखोल अभ्यास"""
    if df.empty or len(df) < 20:
        return None
    x = add_indicators(df)
    l = x.iloc[-1]
    price = float(l["Close"])
    
    raw_atr = l["ATR"] if pd.notna(l["ATR"]) else 0
    atr_val = max(float(raw_atr), price * 0.005)
    
    bull = 0
    bear = 0
    if l["Close"] > l["EMA_21"]: bull += 30
    else: bear += 30
    if l["Close"] > l["VWAP"]: bull += 25
    else: bear += 25
    if l["RSI"] > 55: bull += 25
    elif l["RSI"] < 45: bear += 25
    if l["MACD_HIST"] > 0: bull += 20
    else: bear += 20

    if bull >= 60 and bull > bear:
        action = "BUY / CALL"
        entry = price
        sl = price - (1.2 * atr_val)
        tp = price + (1.8 * atr_val)
    elif bear >= 60 and bear > bull:
        action = "SELL / PUT"
        entry = price
        sl = price + (1.2 * atr_val)
        tp = price - (1.8 * atr_val)
    else:
        action = "NEUTRAL (RANGE)"
        entry = price
        sl = price - (0.8 * atr_val)
        tp = price + (0.8 * atr_val)

    return {
        "name": name,
        "symbol": symbol,
        "price": round(price, 2),
        "action": action,
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "rsi": round(float(l["RSI"]), 1),
        "bias": "BULLISH" if bull > bear else ("BEARISH" if bear > bull else "NEUTRAL")
    }

def build_scanner_row(symbol, df_15m, df_daily, sector="EQUITY"):
    """२४ तास डीप रिसर्च आणि अचूक लेव्हल्स जनरेटर"""
    if df_15m.empty or len(df_15m) < 20:
        return None

    df_15m = add_indicators(df_15m)
    l = df_15m.iloc[-1]
    price = float(l["Close"])
    
    raw_atr = l["ATR"] if pd.notna(l["ATR"]) else 0
    atr = max(float(raw_atr), price * 0.008)

    # Daily Chart Macro Trend Analysis
    daily_trend = "BULLISH"
    if not df_daily.empty and len(df_daily) >= 20:
        df_daily_ind = add_indicators(df_daily)
        if df_daily_ind.iloc[-1]["Close"] < df_daily_ind.iloc[-1]["EMA_50"]:
            daily_trend = "BEARISH"

    reasons = []
    bull_score = 0
    bear_score = 0

    if daily_trend == "BULLISH":
        bull_score += 30
        reasons.append("Daily Macro Trend: अपट्रेंड (Daily EMA 50 वर आधारित)")
    else:
        bear_score += 30
        reasons.append("Daily Macro Trend: डाउनट्रेंड (Daily EMA 50 खाली आधारित)")

    if price > l["VWAP"]:
        bull_score += 25
        reasons.append("Smart Money Flow: संस्थात्मक खरेदीदार ऍक्टिव्ह (Price > VWAP)")
    else:
        bear_score += 25
        reasons.append("Smart Money Flow: सेलिंग प्रेशर ऍक्टिव्ह (Price < VWAP)")

    rsi = float(l["RSI"])
    if rsi > 55:
        bull_score += 25
        reasons.append(f"RSI Momentum: अपवर्ड स्ट्रेंथ ({round(rsi,1)})")
    elif rsi < 45:
        bear_score += 25
        reasons.append(f"RSI Momentum: डाऊनवर्ड प्रेशर ({round(rsi,1)})")

    if l["Close"] > l["EMA_21"]:
        bull_score += 20
        reasons.append("Short-term EMA: 21 EMA वर स्ट्रॉंग सपोर्ट ब्रेकआउट")
    else:
        bear_score += 20
        reasons.append("Short-term EMA: 21 EMA खाली रेझिस्टन्स रिजेक्शन")

    if bull_score >= 60 and daily_trend == "BULLISH":
        action = "BUY"
        sl = round(price - (1.2 * atr), 2)
        tp1 = round(price + (1.5 * atr), 2)
        tp2 = round(price + (2.5 * atr), 2)
        confidence = min(bull_score, 95)
    elif bear_score >= 60 and daily_trend == "BEARISH":
        action = "SELL"
        sl = round(price + (1.2 * atr), 2)
        tp1 = round(price - (1.5 * atr), 2)
        tp2 = round(price - (2.5 * atr), 2)
        confidence = min(bear_score, 95)
    else:
        return None

    return {
        "symbol": symbol,
        "sector": sector,
        "price": round(price, 2),
        "action": action,
        "confidence": confidence,
        "entry": round(price, 2),
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "reasons": reasons[:4]
    }