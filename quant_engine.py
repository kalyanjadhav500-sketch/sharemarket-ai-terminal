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
    v = df['Volume']
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = (tp * v).cumsum() / v.cumsum().replace(0, 1)
    
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
    df['ATR'] = true_range.rolling(14).mean().fillna(df['Close'] * 0.008)
    
    # MACD Calculation
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['SIGNAL'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_HIST'] = df['MACD'] - df['SIGNAL']
    
    return df

def calculate_position_size(entry, sl, total_capital=100000, risk_per_trade_pct=1.5):
    """₹1,00,000 कॅपिटल आणि 1.5% रिस्कनुसार किती शेअर्स घ्यावेत हे ठरवते"""
    risk_amount = total_capital * (risk_per_trade_pct / 100)
    risk_per_share = abs(entry - sl)
    if risk_per_share <= 0:
        return 1
    qty = int(risk_amount / risk_per_share)
    return max(qty, 1)

def analyze_index(symbol, df, name):
    """NIFTY, BANK NIFTY, SENSEX चे सखोल विश्लेषण"""
    if df.empty or len(df) < 20:
        return None
    x = add_indicators(df)
    l = x.iloc[-1]
    price = float(l["Close"])
    atr_val = float(l["ATR"]) if pd.notna(l["ATR"]) and l["ATR"] > 0 else price * 0.005
    
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
        sl = price - (1.0 * atr_val)
        tp = price + (1.8 * atr_val)
    elif bear >= 60 and bear > bull:
        action = "SELL / PUT"
        entry = price
        sl = price + (1.0 * atr_val)
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
    """मल्टी-टाईमफ्रेम, रिस्क कॅल्क्युलेटर आणि कारणांसह स्टॉक फिल्टर"""
    if df_15m.empty or len(df_15m) < 20:
        return None

    df_15m = add_indicators(df_15m)
    l = df_15m.iloc[-1]
    price = float(l["Close"])
    atr = float(l["ATR"]) if pd.notna(l["ATR"]) and l["ATR"] > 0 else price * 0.005

    # Daily Chart वरून ट्रेंड ट्रॅक करणे
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
        reasons.append("Daily Trend: अपट्रेंड (Daily EMA 50 वर)")
    else:
        bear_score += 30
        reasons.append("Daily Trend: डाउनट्रेंड (Daily EMA 50 खाली)")

    if price > l["VWAP"]:
        bull_score += 25
        reasons.append("VWAP: संस्थात्मक खरेदीदार (Price > VWAP)")
    else:
        bear_score += 25
        reasons.append("VWAP: सेलिंग प्रेशर (Price < VWAP)")

    rsi = float(l["RSI"])
    if rsi > 55:
        bull_score += 25
        reasons.append(f"RSI Momentum: स्ट्रॉंग बुलिश झोन ({round(rsi,1)})")
    elif rsi < 45:
        bear_score += 25
        reasons.append(f"RSI Momentum: बेअरिश प्रेशर ({round(rsi,1)})")

    if bull_score >= 55 and daily_trend == "BULLISH":
        action = "BUY"
        sl = round(price - (1.2 * atr), 2)
        tp1 = round(price + (1.5 * atr), 2)
        tp2 = round(price + (2.5 * atr), 2)
        confidence = min(bull_score, 95)
    elif bear_score >= 55 and daily_trend == "BEARISH":
        action = "SELL"
        sl = round(price + (1.2 * atr), 2)
        tp1 = round(price - (1.5 * atr), 2)
        tp2 = round(price - (2.5 * atr), 2)
        confidence = min(bear_score, 95)
    else:
        return None

    qty = calculate_position_size(price, sl)

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
        "qty": qty,
        "reasons": reasons[:3]
    }