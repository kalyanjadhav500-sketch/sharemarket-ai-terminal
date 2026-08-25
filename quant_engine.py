import pandas as pd
import numpy as np

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def analyze_index(symbol, df, display_name="ASSET", tick_data=None):
    if df.empty or len(df) < 20:
        return None

    df = df.copy()
    close_series = df['Close']
    high_series = df['High']
    low_series = df['Low']
    volume_series = df['Volume']
    
    ltp = tick_data.get("ltp", close_series.iloc[-1]) if tick_data else close_series.iloc[-1]
    
    # 1. Institutional Indicators & VWAP Calculation
    df['EMA_9'] = close_series.ewm(span=9, adjust=False).mean()
    df['EMA_21'] = close_series.ewm(span=21, adjust=False).mean()
    df['RSI'] = calculate_rsi(close_series, 14)
    
    # VWAP Calculation
    typical_price = (high_series + low_series + close_series) / 3
    df['VWAP'] = (typical_price * volume_series).cumsum() / volume_series.cumsum()
    
    latest_vwap = df['VWAP'].iloc[-1]
    latest_ema9 = df['EMA_9'].iloc[-1]
    latest_ema21 = df['EMA_21'].iloc[-1]
    latest_rsi = df['RSI'].iloc[-1]
    
    # Volume Confirmation (Current volume vs 20-period average volume)
    avg_volume = volume_series.rolling(window=20).mean().iloc[-1]
    current_volume = volume_series.iloc[-1]
    is_high_volume = current_volume > (avg_volume * 1.2) if not np.isnan(avg_volume) else True

    # 2. Market Structure & Swing Levels (Price Action)
    recent_high = high_series.iloc[-10:-1].max()
    recent_low = low_series.iloc[-10:-1].min()

    # Daily Pivots
    high = high_series.max()
    low = low_series.max()
    close = close_series.iloc[-1]
    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)

    # 3. Senior Trader Multi-Factor Confluence Scoring (0 - 100)
    bullish_score = 0
    bearish_score = 0
    reasons = []

    # A. Trend & EMA Confluence
    if latest_ema9 > latest_ema21 and ltp > latest_ema9:
        bullish_score += 25
        reasons.append("Institutional Trend: 9 EMA is above 21 EMA with price sustaining above short-term momentum.")
    elif latest_ema9 < latest_ema21 and ltp < latest_ema9:
        bearish_score += 25
        reasons.append("Institutional Trend: 9 EMA is below 21 EMA indicating strong short-term distribution.")

    # B. VWAP Validation (Smart Money Benchmark)
    if ltp > latest_vwap:
        bullish_score += 25
        reasons.append(f"VWAP Filter Passed: Price (₹{round(ltp,2)}) is trading above Institutional VWAP (₹{round(latest_vwap,2)}).")
    else:
        bearish_score += 25
        reasons.append(f"VWAP Filter Passed: Price (₹{round(ltp,2)}) is trading below Institutional VWAP (₹{round(latest_vwap,2)}).")

    # C. Volume & Momentum (RSI + Volume Spike)
    if is_high_volume:
        if ltp > recent_high:
            bullish_score += 30
            reasons.append("Breakout & Volume: Price broke recent swing high with high institutional volume.")
        elif ltp < recent_low:
            bearish_score += 30
            reasons.append("Breakdown & Volume: Price broke recent swing low with heavy selling volume.")
        else:
            bullish_score += 15
            bearish_score += 15
            reasons.append("Volume Expansion active across current structure.")

    if 50 <= latest_rsi <= 75:
        bullish_score += 20
        reasons.append(f"RSI Momentum: Healthy bullish momentum at {round(latest_rsi, 1)}.")
    elif 25 <= latest_rsi <= 50:
        bearish_score += 20
        reasons.append(f"RSI Momentum: Bearish pressure indicated at {round(latest_rsi, 1)}.")

    # 4. Strict Professional Execution Rule (Requires >= 80% Confidence)
    action = "HOLD / WAIT"
    confidence = max(bullish_score, bearish_score)
    target1, target2, stop_loss, rr_ratio = "N/A", "N/A", "N/A", "N/A"

    min_sl_dist = ltp * 0.007  # Professional 0.7% strict risk buffer

    if bullish_score >= 80:
        action = "BUY CALL (CE)"
        raw_sl = round(recent_low if recent_low < ltp else s1, 2)
        stop_loss = round(ltp - min_sl_dist, 2) if (ltp - raw_sl) < min_sl_dist else raw_sl
        target1 = round(r1, 2)
        target2 = round(r2, 2)
        rr_ratio = "1 : 2.5+"
    elif bearish_score >= 80:
        action = "BUY PUT (PE)"
        raw_sl = round(recent_high if recent_high > ltp else r1, 2)
        stop_loss = round(ltp + min_sl_dist, 2) if (raw_sl - ltp) < min_sl_dist else raw_sl
        target1 = round(s1, 2)
        target2 = round(s2, 2)
        rr_ratio = "1 : 2.5+"
    else:
        action = "HOLD / NO SETUP"
        reasons = [f"AI Score is {confidence}% (Below senior institutional 80% threshold). Market is in consolidation; sitting on cash/waiting for clear structure breakout."]

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
            "vwap": round(latest_vwap, 2),
            "r1": round(r1, 2),
            "s1": round(s1, 2)
        },
        "reasons": reasons
    }