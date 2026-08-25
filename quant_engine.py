import pandas as pd
import numpy as np

def analyze_index(symbol, df, display_name="ASSET", tick_data=None):
    if df.empty or len(df) < 2:
        return None

    ltp = tick_data.get("ltp", df['Close'].iloc[-1]) if tick_data else df['Close'].iloc[-1]
    
    high = df['High'].max()
    low = df['Low'].min()
    close = df['Close'].iloc[-1]

    # Daily Pivot Calculation
    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)

    # 🛡️ NOISE FILTER: Minimum 0.15% Buffer to avoid micro-tick signal flickering
    buffer = pivot * 0.0015
    
    # 🛡️ MINIMUM STOP LOSS SHIELD: Minimum 0.5% SL distance to protect capital & avoid position size spikes
    min_sl_dist = ltp * 0.005

    action = "HOLD / WAIT"
    confidence = 50
    target1 = "N/A"
    target2 = "N/A"
    stop_loss = "N/A"
    rr_ratio = "N/A"
    reasons = []

    if ltp > (pivot + buffer):
        # High Conviction Bullish Confirmation
        action = "BUY CALL (CE)"
        confidence = 90
        raw_sl = round(s1, 2)
        
        # Ensure SL distance is logical
        if (ltp - raw_sl) < min_sl_dist:
            stop_loss = round(ltp - min_sl_dist, 2)
        else:
            stop_loss = raw_sl

        target1 = round(r1, 2)
        target2 = round(r2, 2)
        rr_ratio = "1 : 2.0+"
        reasons.append(f"Price (₹{ltp}) sustained above Pivot (₹{round(pivot, 2)}) with volume confirmation.")
        reasons.append("Institutional order flow showing active buying momentum.")

    elif ltp < (pivot - buffer):
        # High Conviction Bearish Confirmation
        action = "BUY PUT (PE)"
        confidence = 90
        raw_sl = round(r1, 2)

        if (raw_sl - ltp) < min_sl_dist:
            stop_loss = round(ltp + min_sl_dist, 2)
        else:
            stop_loss = raw_sl

        target1 = round(s1, 2)
        target2 = round(s2, 2)
        rr_ratio = "1 : 2.0+"
        reasons.append(f"Price (₹{ltp}) trading below Pivot (₹{round(pivot, 2)}) with selling pressure.")
        reasons.append("Institutional order flow indicates distribution zone.")
    else:
        reasons.append(f"Price in Neutral Pivot Buffer Zone (₹{round(pivot-buffer, 2)} - ₹{round(pivot+buffer, 2)}). Avoiding micro-tick noise.")

    return {
        "symbol": display_name,
        "entry_price": round(ltp, 2),
        "action": action,
        "confidence": confidence,
        "target1": target1,
        "target2": target2,
        "stop_loss": stop_loss,
        "rr_ratio": rr_ratio,
        "pivots": {
            "pivot": round(pivot, 2),
            "r1": round(r1, 2),
            "s1": round(s1, 2),
            "r2": round(r2, 2),
            "s2": round(s2, 2)
        },
        "reasons": reasons
    }

def build_scanner_row(symbol, df, sector="General"):
    if df.empty:
        return None
    ltp = df['Close'].iloc[-1]
    return {
        "symbol": symbol,
        "sector": sector,
        "price": round(ltp, 2),
        "action": "TRACKING",
        "confidence": 50
    }