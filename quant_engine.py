import pandas as pd
import numpy as np

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def analyze_index(symbol, df, display_name="ASSET", tick_data=None):
    if df.empty or len(df) < 15:
        return None

    # Working on latest confirmed data
    df = df.copy()
    close_series = df['Close']
    
    ltp = tick_data.get("ltp", close_series.iloc[-1]) if tick_data else close_series.iloc[-1]
    
    # 1. Technical Indicators (Deep Analysis)
    df['EMA_20'] = close_series.ewm(span=20, adjust=False).mean()
    df['EMA_50'] = close_series.ewm(span=50, adjust=False).mean()
    df['RSI'] = calculate_rsi(close_series, 14)

    latest_ema20 = df['EMA_20'].iloc[-1]
    latest_ema50 = df['EMA_50'].iloc[-1]
    latest_rsi = df['RSI'].iloc[-1]

    # 2. Daily Pivots
    high = df['High'].max()
    low = df['Low'].min()
    close = close_series.iloc[-1]

    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)

    # 3. Multi-Factor AI Confluence Scoring (0 - 100)
    bullish_score = 0
    bearish_score = 0
    reasons = []

    # Trend Factor
    if ltp > latest_ema20 and latest_ema20 > latest_ema50:
        bullish_score += 35
        reasons.append("Strong Uptrend: Price is sustaining above 20 EMA & 50 EMA.")
    elif ltp < latest_ema20 and latest_ema20 < latest_ema50:
        bearish_score += 35
        reasons.append("Strong Downtrend: Price is trading below 20 EMA & 50 EMA.")

    # Momentum Factor (RSI)
    if 55 <= latest_rsi <= 70:
        bullish_score += 30
        reasons.append(f"Bullish Momentum: RSI is strong at {round(latest_rsi, 1)}.")
    elif 30 <= latest_rsi <= 45:
        bearish_score += 30
        reasons.append(f"Bearish Momentum: RSI is weak at {round(latest_rsi, 1)}.")

    # Pivot Structure Factor
    if ltp > pivot:
        bullish_score += 35
        reasons.append(f"Structural Support: Price (₹{round(ltp,2)}) trading above Central Pivot (₹{round(pivot,2)}).")
    else:
        bearish_score += 35
        reasons.append(f"Structural Resistance: Price (₹{round(ltp,2)}) trading below Central Pivot (₹{round(pivot,2)}).")

    # 4. Final Stable Execution Logic (Requires Minimum 75% AI Score)
    action = "HOLD / WAIT"
    confidence = max(bullish_score, bearish_score)
    target1, target2, stop_loss, rr_ratio = "N/A", "N/A", "N/A", "N/A"

    min_sl_dist = ltp * 0.008  # Strict 0.8% SL Buffer to prevent position sizing jumps

    if bullish_score >= 75:
        action = "BUY CALL (CE)"
        raw_sl = round(s1, 2)
        stop_loss = round(ltp - min_sl_dist, 2) if (ltp - raw_sl) < min_sl_dist else raw_sl
        target1 = round(r1, 2)
        target2 = round(r2, 2)
        rr_ratio = "1 : 2.5+"
    elif bearish_score >= 75:
        action = "BUY PUT (PE)"
        raw_sl = round(r1, 2)
        stop_loss = round(ltp + min_sl_dist, 2) if (raw_sl - ltp) < min_sl_dist else raw_sl
        target1 = round(s1, 2)
        target2 = round(s2, 2)
        rr_ratio = "1 : 2.5+"
    else:
        action = "HOLD / NO TRADE"
        reasons = [f"AI Score is {confidence}% (Below required 75% threshold). Waiting for clear market setup."]

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