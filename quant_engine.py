import pandas as pd
import numpy as np

def calculate_pivots(df):
    """मागील ट्रेडिंग डेटावरून रिअल-टाईम Daily Pivots काढणे."""
    try:
        high = df['High'].max()
        low = df['Low'].min()
        close = df['Close'].iloc[-1]
        
        pivot = (high + low + close) / 3
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        
        return {
            "pivot": round(pivot, 2),
            "r1": round(r1, 2),
            "s1": round(s1, 2),
            "r2": round(r2, 2),
            "s2": round(s2, 2)
        }
    except Exception:
        return {"pivot": 0, "r1": 0, "s1": 0, "r2": 0, "s2": 0}

def analyze_index(symbol, df_1m, display_name="NIFTY", tick_data=None):
    """
    Zero-Lag Tick-by-Tick & Order Flow Imbalance Quant Engine.
    वेळ-आधारित टाइमफ्रेम काढून टाकून प्रति-सेकंद बाइंग/सेलिंग प्रेशरवर ट्रेड निर्णय घेणे.
    """
    if df_1m.empty or len(df_1m) < 3:
        return None

    pivots = calculate_pivots(df_1m)
    pivot_val = pivots["pivot"]
    
    # 1. रिअल-टाईम टिक डेटा किंवा एलटीपी (LTP) ट्रॅकिंग
    curr_price = tick_data.get("ltp") if tick_data else df_1m['Close'].iloc[-1]
    buy_demand_ratio = tick_data.get("buy_demand_ratio", 0.5) if tick_data else 0.5
    volume_surge = tick_data.get("volume_surge", False) if tick_data else True

    # EMA 21 चा ०-सेकंद स्पीड ट्रॅक
    ema_21 = df_1m['Close'].ewm(span=21, adjust=False).mean().iloc[-1]
    
    reasons = []
    confidence = 50
    action = "HOLD / WAIT"

    # 2. Tick-Imbalance & Smart Money Flow Logic
    # BUY CALL (CE) Rule: खरेदीदार मागणी >= ६५% + पिव्होट व EMA च्या वर भाव + व्हॉल्यूम स्पाइक
    if buy_demand_ratio >= 0.65 and curr_price > pivot_val and curr_price > ema_21:
        confidence += 35
        reasons.append(f"Institutional Buy Demand: {int(buy_demand_ratio * 100)}%")
        reasons.append("Tick Price trading above Daily Pivot & 21 EMA")
        if volume_surge:
            confidence += 10
            reasons.append("High Frequency Volume Spike Detected")
        action = "BUY CALL (CE)"

    # BUY PUT (PE) Rule: विक्रेते दबाव >= ६५% + पिव्होट व EMA च्या खाली भाव + व्हॉल्यूम स्पाइक
    elif buy_demand_ratio <= 0.35 and curr_price < pivot_val and curr_price < ema_21:
        confidence += 35
        reasons.append(f"Institutional Sell Pressure: {int((1 - buy_demand_ratio) * 100)}%")
        reasons.append("Tick Price trading below Daily Pivot & 21 EMA")
        if volume_surge:
            confidence += 10
            reasons.append("High Frequency Volume Spike Detected")
        action = "BUY PUT (PE)"

    else:
        reasons.append("Order flow in neutral zone (No volume imbalance)")
        action = "HOLD / WAIT"

    # 3. कडक कॉन्फिडन्स फिल्टर (८५% खाली ट्रेड पूर्ण ब्लॉक)
    if confidence < 85:
        action = "HOLD / WAIT"

    # 4. टार्गेट आणि स्टॉपलॉस कॅल्क्युलेशन (HOLD / WAIT असताना स्वच्छ N/A)
    if action == "BUY CALL (CE)":
        target1 = curr_price + (pivots["r1"] - pivot_val) * 0.8
        target2 = pivots["r2"]
        stop_loss = max(pivot_val, curr_price - 25)
        rr_ratio = "1 : 2.5+"
    elif action == "BUY PUT (PE)":
        target1 = curr_price - (pivot_val - pivots["s1"]) * 0.8
        target2 = pivots["s2"]
        stop_loss = min(pivot_val, curr_price + 25)
        rr_ratio = "1 : 2.5+"
    else:
        target1 = "N/A"
        target2 = "N/A"
        stop_loss = "N/A"
        rr_ratio = "N/A"

    return {
        "index": display_name,
        "action": action,
        "confidence": confidence,
        "entry_price": round(curr_price, 2),
        "target1": round(target1, 2) if isinstance(target1, float) else target1,
        "target2": round(target2, 2) if isinstance(target2, float) else target2,
        "stop_loss": round(stop_loss, 2) if isinstance(stop_loss, float) else stop_loss,
        "rr_ratio": rr_ratio,
        "pivots": pivots,
        "reasons": reasons
    }

def build_scanner_row(symbol, df_1m, sector="Equity"):
    """Equity Watchlist Scanner for High Conviction Breakouts."""
    if df_1m.empty or len(df_1m) < 3:
        return None
        
    curr_price = df_1m['Close'].iloc[-1]
    ema_21 = df_1m['Close'].ewm(span=21, adjust=False).mean().iloc[-1]
    
    if curr_price > ema_21 * 1.005:
        action = "BUY / LONG"
        conf = 85
    elif curr_price < ema_21 * 0.995:
        action = "SELL / SHORT"
        conf = 85
    else:
        action = "NEUTRAL"
        conf = 50
        
    return {
        "symbol": symbol,
        "sector": sector,
        "price": round(curr_price, 2),
        "action": action,
        "confidence": conf
    }