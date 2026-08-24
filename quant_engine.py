import pandas as pd
import numpy as np

# --- INSTITUTIONAL AI AGENT SYSTEM PROMPT ---
AI_AGENT_PROMPT = """
You are an Elite Institutional Trading AI Agent specializing in Indian Markets (NSE/BSE).
Your Primary Goal: Real-Money Capital Protection & High Win-Rate Execution (Minimum Risk-to-Reward 1:1.5).

Rules Enforced:
1. MARKET STRUCTURE:
   - Price > VWAP & Price > EMA 21 & RSI > 55 -> BUY CALL (CE) / LONG
   - Price < VWAP & Price < EMA 21 & RSI < 45 -> BUY PUT (PE) / SHORT
   - Squeezed between VWAP & EMA (Choppy) -> NO TRADE ZONE (Protect Capital)

2. RISK MANAGEMENT:
   - Dynamic Stop Loss (1.0x ATR)
   - Target 1 (1.5x ATR), Target 2 (2.5x ATR)
"""

def add_indicators(df):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or len(df) < 10:
        return df
    
    df = df.copy()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
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
    df['ATR'] = np.max(ranges, axis=1).rolling(14).mean()
    
    return df

def analyze_index(symbol, df_15m, display_name=None):
    """System Prompt वर आधारित ऑप्शन्स सिग्नल इंजिन"""
    if df_15m is None or not isinstance(df_15m, pd.DataFrame) or df_15m.empty or len(df_15m) < 10:
        return None
    
    name = display_name if display_name else symbol
    df_15m = add_indicators(df_15m)
    l = df_15m.iloc[-1]
    price = float(l["Close"])
    vwap = float(l["VWAP"]) if pd.notna(l["VWAP"]) else price
    ema21 = float(l["EMA_21"]) if pd.notna(l["EMA_21"]) else price
    rsi = float(l["RSI"]) if pd.notna(l["RSI"]) else 50
    raw_atr = l["ATR"] if pd.notna(l["ATR"]) else 0
    atr = max(float(raw_atr), price * 0.0035)
    
    reasons = []
    
    # 1. Bearish Signal Logic (BUY PUT)
    if price < vwap and price < ema21 and rsi < 50:
        trend = "BEARISH (मार्केट खाली पडणार)"
        action = "BUY PUT (PE)"
        sl = round(price + (1.0 * atr), 2)
        tp1 = round(price - (1.5 * atr), 2)
        tp2 = round(price - (2.5 * atr), 2)
        reasons.append("Institutional Selling: Price VWAP च्या खाली ट्रॅप झाली आहे.")
        reasons.append("Momentum: EMA 21 च्या खाली ब्रेकडाऊन झाला आहे.")
        reasons.append(f"RSI Weakness: Index {round(rsi, 1)} (सेलिंग प्रेशर जास्त आहे)")
        confidence = 88
        
    # 2. Bullish Signal Logic (BUY CALL)
    elif price > vwap and price > ema21 and rsi > 50:
        trend = "BULLISH (मार्केट वर जाणार)"
        action = "BUY CALL (CE)"
        sl = round(price - (1.0 * atr), 2)
        tp1 = round(price + (1.5 * atr), 2)
        tp2 = round(price + (2.5 * atr), 2)
        reasons.append("Institutional Buying: Price VWAP च्या वर ट्रेड करत आहे.")
        reasons.append("Momentum: EMA 21 च्या वर स्ट्रॉंग बाइंग आहे.")
        reasons.append(f"RSI Strength: Index {round(rsi, 1)} (बायर्स कंट्रोलमध्ये आहेत)")
        confidence = 88
        
    # 3. Capital Protection Rule (NO TRADE ZONE)
    else:
        trend = "SIDEWAYS (मार्केट रेंजबाऊंड आहे)"
        action = "NO TRADE (थांबा आणि पहा)"
        sl = round(price, 2)
        tp1 = round(price, 2)
        tp2 = round(price, 2)
        reasons.append("Capital Protection Rule: Price VWAP आणि EMA च्या मध्ये अडकली आहे.")
        reasons.append("No Clear Direction: खोटा ट्रेड घेऊन नुकसान टाळण्यासाठी AI ने थांबण्याचा सल्ला दिला आहे.")
        confidence = 95

    return {
        "name": name, "symbol": symbol, "trend": trend, "price": round(price, 2),
        "action": action, "entry": round(price, 2), "sl": sl, "tp1": tp1, "tp2": tp2,
        "rsi": round(rsi, 1), "confidence": confidence, "reasons": reasons
    }

def build_scanner_row(symbol, df_15m, df_daily=None, *args, **kwargs):
    """Equity Stocks AI Scanner Logic"""
    if df_15m is None or not isinstance(df_15m, pd.DataFrame) or df_15m.empty or len(df_15m) < 10:
        return None

    df_15m = add_indicators(df_15m)
    l = df_15m.iloc[-1]
    price = float(l["Close"])
    vwap = float(l["VWAP"]) if pd.notna(l["VWAP"]) else price
    ema21 = float(l["EMA_21"]) if pd.notna(l["EMA_21"]) else price
    rsi = float(l["RSI"]) if pd.notna(l["RSI"]) else 50
    raw_atr = l["ATR"] if pd.notna(l["ATR"]) else 0
    atr = max(float(raw_atr), price * 0.005)

    reasons = []
    
    if price < vwap and price < ema21:
        trend = "BEARISH (खाली पडणार)"
        action = "SELL / SHORT"
        sl = round(price + (1.0 * atr), 2)
        tp1 = round(price - (1.5 * atr), 2)
        tp2 = round(price - (2.5 * atr), 2)
        reasons.append("Price below VWAP & EMA 21")
        confidence = 85
    elif price > vwap and price > ema21:
        trend = "BULLISH (वर जाणार)"
        action = "BUY / LONG"
        sl = round(price - (1.0 * atr), 2)
        tp1 = round(price + (1.5 * atr), 2)
        tp2 = round(price + (2.5 * atr), 2)
        reasons.append("Price above VWAP & EMA 21")
        confidence = 85
    else:
        trend = "SIDEWAYS"
        action = "WAIT / NO TRADE"
        sl = price
        tp1 = price
        tp2 = price
        reasons.append("No clear momentum")
        confidence = 90

    return {
        "name": symbol, "symbol": symbol, "trend": trend, "price": round(price, 2),
        "action": action, "confidence": confidence, "entry": round(price, 2),
        "sl": sl, "tp1": tp1, "tp2": tp2, "reasons": reasons
    }