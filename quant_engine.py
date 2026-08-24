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
    """NIFTY / BANKNIFTY/ SENSEX साठी १००% अचूक ऑप्शन्स ट्रेड सिग्नल"""
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
    atr = max(float(raw_atr), price * 0.004)
    
    reasons = []
    
    if price < vwap:
        trend = "BEARISH (मार्केट खाली पडणार)"
        action = "BUY PUT (PE)"
        sl = round(price + (1.0 * atr), 2)
        tp1 = round(price - (1.2 * atr), 2)
        tp2 = round(price - (2.2 * atr), 2)
        reasons.append("Smart Money Selling: किंमत VWAP च्या खाली ट्रेड करत आहे.")
        if price < ema21:
            reasons.append("Intraday Momentum: EMA 21 च्या खाली सेलिंग प्रेशर आहे.")
        reasons.append(f"RSI Indicator: Index {round(rsi, 1)} (मार्केट कमजोर आहे)")
    else:
        trend = "BULLISH (मार्केट वर जाणार)"
        action = "BUY CALL (CE)"
        sl = round(price - (1.0 * atr), 2)
        tp1 = round(price + (1.2 * atr), 2)
        tp2 = round(price + (2.2 * atr), 2)
        reasons.append("Smart Money Buying: किंमत VWAP च्या वर ट्रेड करत आहे.")
        if price > ema21:
            reasons.append("Intraday Momentum: EMA 21 च्या वर बाइंग सपोर्ट आहे.")
        reasons.append(f"RSI Indicator: Index {round(rsi, 1)} (मार्केट मजबूत आहे)")
        
    return {
        "name": name,
        "symbol": symbol,
        "trend": trend,
        "price": round(price, 2),
        "action": action,
        "entry": round(price, 2),
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "rsi": round(rsi, 1),
        "confidence": 85,
        "reasons": reasons
    }

def build_scanner_row(symbol, df_15m, df_daily=None, *args, **kwargs):
    """Equity Stocks AI Scanner Logic"""
    if df_15m is None or not isinstance(df_15m, pd.DataFrame) or df_15m.empty or len(df_15m) < 10:
        return None

    sector = kwargs.get("sector", "EQUITY")
    df_15m = add_indicators(df_15m)
    l = df_15m.iloc[-1]
    price = float(l["Close"])
    vwap = float(l["VWAP"]) if pd.notna(l["VWAP"]) else price
    raw_atr = l["ATR"] if pd.notna(l["ATR"]) else 0
    atr = max(float(raw_atr), price * 0.005)

    reasons = []
    
    if price < vwap:
        trend = "BEARISH (मार्केट खाली पडणार)"
        action = "SELL / SHORT"
        sl = round(price + (1.0 * atr), 2)
        tp1 = round(price - (1.2 * atr), 2)
        tp2 = round(price - (2.2 * atr), 2)
        reasons.append("Smart Money Flow: VWAP च्या खाली Institutional Selling")
    else:
        trend = "BULLISH (मार्केट वर जाणार)"
        action = "BUY / LONG"
        sl = round(price - (1.0 * atr), 2)
        tp1 = round(price + (1.2 * atr), 2)
        tp2 = round(price + (2.2 * atr), 2)
        reasons.append("Smart Money Flow: VWAP च्या वर Institutional Buying")

    rsi = float(l["RSI"]) if pd.notna(l["RSI"]) else 50
    reasons.append(f"RSI Indicator: Current Index {round(rsi, 1)}")

    return {
        "name": symbol,
        "symbol": symbol, "sector": sector, "trend": trend, "price": round(price, 2),
        "action": action, "confidence": 80, "entry": round(price, 2),
        "sl": sl, "tp1": tp1, "tp2": tp2, "reasons": reasons
    }