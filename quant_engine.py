import pandas as pd
import numpy as np

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    
    # EMAs Calculation
    df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # RSI Calculation
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))
    df['rsi'] = df['rsi'].fillna(50)
    
    # VWAP Calculation
    if 'volume' in df.columns:
        v = df['volume']
        tp = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (tp * v).cumsum() / v.cumsum().replace(0, np.nan)
        df['vwap'] = df['vwap'].ffill().bfill()
    else:
        df['vwap'] = df['close']
        
    return df

def analyze_institutional_matrix(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 5:
        return {
            "bull_score": 0, "bear_score": 0, "regime": "NEUTRAL",
            "action": "HOLD / WAIT", "confidence": 0, "price": 0.0,
            "sl": 0.0, "tp1": 0.0, "tp2": 0.0, "reasons": ["पुरेशा डेटा उपलब्ध नाही"]
        }
    
    df = calculate_indicators(df)
    latest = df.iloc[-1]
    
    bull_score = 0
    bear_score = 0
    reasons = []
    
    # Trend Analysis
    if latest['close'] > latest['ema_20']:
        bull_score += 25
        reasons.append("किंमत EMA 20 च्या वर आहे (Bullish)")
    else:
        bear_score += 25
        reasons.append("किंमत EMA 20 च्या खाली आहे (Bearish)")
        
    if latest['ema_9'] > latest['ema_20']:
        bull_score += 25
        reasons.append("EMA 9/20 बुलिश क्रॉसओव्हर")
    else:
        bear_score += 25
        reasons.append("EMA 9/20 बेरिश क्रॉसओव्हर")
        
    if latest['rsi'] > 55:
        bull_score += 25
        reasons.append(f"RSI बळकट आहे ({latest['rsi']:.1f})")
    elif latest['rsi'] < 45:
        bear_score += 25
        reasons.append(f"RSI कमकुवत आहे ({latest['rsi']:.1f})")
        
    if latest['close'] > latest['vwap']:
        bull_score += 25
        reasons.append("किंमत VWAP च्या वर ट्रेड करत आहे")
    else:
        bear_score += 25
        reasons.append("किंमत VWAP च्या खाली ट्रेड करत आहे")

    price = round(float(latest['close']), 2)
    regime = "STRONG BULLISH" if bull_score >= 75 else ("STRONG BEARISH" if bear_score >= 75 else "NEUTRAL / CHOPPY")
    
    action = "HOLD / WAIT"
    sl, tp1, tp2 = price, price, price
    confidence = max(bull_score, bear_score)
    
    if bull_score >= 60:
        action = "BUY / LONG"
        sl = round(price * 0.99, 2)
        tp1 = round(price * 1.015, 2)
        tp2 = round(price * 1.03, 2)
    elif bear_score >= 60:
        action = "SELL / SHORT"
        sl = round(price * 1.01, 2)
        tp1 = round(price * 0.985, 2)
        tp2 = round(price * 0.97, 2)

    return {
        "bull_score": bull_score,
        "bear_score": bear_score,
        "regime": regime,
        "action": action,
        "confidence": confidence,
        "price": price,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "reasons": reasons
    }

def analyze_index(symbol: str, df: pd.DataFrame, display_name="INDEX") -> dict:
    res = analyze_institutional_matrix(df)
    res["name"] = display_name
    res["symbol"] = symbol
    return res

def build_scanner_row(symbol: str, df: pd.DataFrame, sector="Equity") -> dict:
    res = analyze_institutional_matrix(df)
    res["symbol"] = symbol
    res["sector"] = sector
    return res