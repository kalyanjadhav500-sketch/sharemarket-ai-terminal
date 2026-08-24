import pandas as pd
import numpy as np

def add_indicators(df):
    """इन्स्टिट्युशनल लेव्हल तांत्रिक इंडिकेटर्स (Volume Spike + VWAP + RSI + ATR)"""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or len(df) < 15:
        return df
    
    df = df.copy()
    
    # Exponential Moving Averages
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    # Average Volume & Spike Filter
    df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
    
    # VWAP Calculation (Institutional Flow)
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
    
    # ATR Calculation (Volatile StopLoss Control)
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
    """मार्केटची अचूक दिशा आणि स्ट्रेंथ मोजणे"""
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
    if l['MACD_HIST'] > 0: bull += 20
    else: bear += 20
    
    reg_str = "BULLISH" if bull > bear else ("BEARISH" if bear > bull else "NEUTRAL")
    score = max(bull, bear)
    
    return {"regime": reg_str, "confidence": score, "score": score, "bull": bull, "bear": bear}

def sector_strength(sector_data=None):
    return {"BANKING": "BULLISH", "IT": "BULLISH", "AUTO": "NEUTRAL"}

def analyze_index(symbol, df, name):
    """NIFTY / BANK NIFTY / SENSEX चे अचूक लेव्हल्स"""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or len(df) < 20:
        return None
    x = add_indicators(df)
    l = x.iloc[-1]
    price = float(l["Close"])
    
    raw_atr = l["ATR"] if pd.notna(l["ATR"]) else 0
    atr_val = max(float(raw_atr), price * 0.005)
    
    regime = market_regime(df)
    bull, bear = regime["bull"], regime["bear"]

    if bull >= 60 and bull > bear:
        action = "BUY / CALL"
        entry = price
        sl = price - (1.0 * atr_val)
        tp = price + (2.0 * atr_val)
    elif bear >= 60 and bear > bull:
        action = "SELL / PUT"
        entry = price
        sl = price + (1.0 * atr_val)
        tp = price - (2.0 * atr_val)
    else:
        action = "NEUTRAL (WAIT)"
        entry = price
        sl = price - (0.5 * atr_val)
        tp = price + (0.5 * atr_val)

    return {
        "name": name, "symbol": symbol, "price": round(price, 2),
        "action": action, "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
        "rsi": round(float(l["RSI"]), 1), "bias": regime["regime"]
    }

def build_scanner_row(symbol, df_15m, df_daily=None, *args, **kwargs):
    """हाय-ॲक्युरसी AI ट्रेड सिग्नल जनरेटर"""
    if df_15m is None or not isinstance(df_15m, pd.DataFrame) or df_15m.empty or len(df_15m) < 20:
        return None

    sector = kwargs.get("sector", "EQUITY")
    if args and len(args) >= 2 and isinstance(args[-1], str):
        sector = args[-1]

    df_15m = add_indicators(df_15m)
    l = df_15m.iloc[-1]
    price = float(l["Close"])
    
    raw_atr = l["ATR"] if pd.notna(l["ATR"]) else 0
    atr = max(float(raw_atr), price * 0.006)

    # 1. Macro Trend Filter (Daily Chart)
    daily_trend = "BULLISH"
    if df_daily is not None and isinstance(df_daily, pd.DataFrame) and not df_daily.empty and len(df_daily) >= 20:
        df_daily_ind = add_indicators(df_daily)
        if df_daily_ind.iloc[-1]["Close"] < df_daily_ind.iloc[-1]["EMA_50"]:
            daily_trend = "BEARISH"

    reasons = []
    bull_score = 0
    bear_score = 0

    # Trend Logic
    if daily_trend == "BULLISH":
        bull_score += 30
        reasons.append("Macro Trend: Daily Up-Trend ✅")
    else:
        bear_score += 30
        reasons.append("Macro Trend: Daily Down-Trend ⚠️")

    # Smart Money Flow
    if price > l["VWAP"]:
        bull_score += 25
        reasons.append("Institutional Flow: Price VWAP च्या वर (Buyers Heavy) 📈")
    else:
        bear_score += 25
        reasons.append("Institutional Flow: Price VWAP च्या खाली (Sellers Heavy) 📉")

    # Volume Spike Filter
    vol_curr = float(l["Volume"]) if pd.notna(l["Volume"]) else 0
    vol_avg = float(l["Vol_SMA20"]) if pd.notna(l["Vol_SMA20"]) else 1
    if vol_curr > (1.3 * vol_avg):
        if bull_score > bear_score: bull_score += 15
        else: bear_score += 15
        reasons.append(f"Volume Spike: 20-SMA पेक्षा {round(vol_curr/vol_avg, 1)}x जास्त व्हॉल्यूम 🔥")

    # RSI Safety Zone
    rsi = float(l["RSI"])
    if 55 <= rsi <= 68:
        bull_score += 20
        reasons.append(f"RSI Momentum: स्ट्रॉंग झोन ({round(rsi,1)})")
    elif 32 <= rsi <= 45:
        bear_score += 20
        reasons.append(f"RSI Momentum: विक झोन ({round(rsi,1)})")
    elif rsi > 70 or rsi < 30:
        return None # Overbought/Oversold trap टाळण्यासाठी नो ट्रेड!

    # Strict Final Decision (Minimum 70% Conviction Required)
    if bull_score >= 70 and daily_trend == "BULLISH":
        action = "BUY"
        sl = round(price - (1.0 * atr), 2)
        tp1 = round(price + (1.5 * atr), 2)
        tp2 = round(price + (2.5 * atr), 2)
        confidence = min(bull_score, 95)
    elif bear_score >= 70 and daily_trend == "BEARISH":
        action = "SELL"
        sl = round(price + (1.0 * atr), 2)
        tp1 = round(price - (1.5 * atr), 2)
        tp2 = round(price - (2.5 * atr), 2)
        confidence = min(bear_score, 95)
    else:
        return None  # बळजबरीने कॉल नाही!

    return {
        "symbol": symbol, "sector": sector, "price": round(price, 2),
        "action": action, "confidence": confidence, "entry": round(price, 2),
        "sl": sl, "tp1": tp1, "tp2": tp2, "qty": 1, "reasons": reasons
    }