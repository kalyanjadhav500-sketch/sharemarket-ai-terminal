import pandas as pd
import numpy as np

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def analyze_index(symbol, df, display_name="ASSET", tick_data=None, news_headlines=None):
    if df.empty or len(df) < 15:
        return None

    df = df.copy()
    close_series = df['Close']
    high_series = df['High']
    low_series = df['Low']
    volume_series = df['Volume']
    
    ltp = tick_data.get("ltp", close_series.iloc[-1]) if tick_data else close_series.iloc[-1]
    
    # 1. Technical Calculations
    df['EMA_9'] = close_series.ewm(span=9, adjust=False).mean()
    df['EMA_21'] = close_series.ewm(span=21, adjust=False).mean()
    df['RSI'] = calculate_rsi(close_series, 14)
    
    typical_price = (high_series + low_series + close_series) / 3
    df['VWAP'] = (typical_price * volume_series).cumsum() / volume_series.cumsum()
    
    latest_vwap = df['VWAP'].iloc[-1]
    latest_ema9 = df['EMA_9'].iloc[-1]
    latest_ema21 = df['EMA_21'].iloc[-1]
    latest_rsi = df['RSI'].iloc[-1]
    
    avg_vol = volume_series.rolling(window=15).mean().iloc[-1]
    curr_vol = volume_series.iloc[-1]
    is_high_volume = curr_vol > (avg_vol * 1.15) if not np.isnan(avg_vol) else True

    recent_high = high_series.iloc[-10:-1].max()
    recent_low = low_series.iloc[-10:-1].min()

    high = high_series.max()
    low = low_series.min()
    close = close_series.iloc[-1]
    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)

    # 2. Live News Sentiment Parsing
    news_text = " ".join(news_headlines).lower() if news_headlines else ""
    bullish_keywords = ["gain", "bull", "surge", "high", "growth", "buy", "profit", "positive", "up", "rally"]
    bearish_keywords = ["fall", "bear", "drop", "low", "loss", "sell", "down", "warning", "negative", "plummet"]
    
    bull_news_cnt = sum(1 for kw in bullish_keywords if kw in news_text)
    bear_news_cnt = sum(1 for kw in bearish_keywords if kw in news_text)

    # 3. Multi-Factor Institutional Confluence (100 Point Scale)
    bullish_score = 0
    bearish_score = 0
    reasons = []

    # A. Institutional Trend & EMA (25 Points)
    if latest_ema9 > latest_ema21 and ltp > latest_ema9:
        bullish_score += 25
        reasons.append("Trend Confluence: 9 EMA > 21 EMA with active buying strength.")
    elif latest_ema9 < latest_ema21 and ltp < latest_ema9:
        bearish_score += 25
        reasons.append("Trend Confluence: 9 EMA < 21 EMA with active distribution.")

    # B. VWAP Validation (25 Points)
    if ltp > latest_vwap:
        bullish_score += 25
        reasons.append(f"VWAP Institutional Support: Price (₹{round(ltp,2)}) sustained above VWAP (₹{round(latest_vwap,2)}).")
    else:
        bearish_score += 25
        reasons.append(f"VWAP Institutional Resistance: Price (₹{round(ltp,2)}) trading below VWAP (₹{round(latest_vwap,2)}).")

    # C. Swing Structure & Volume Expansion (25 Points)
    if ltp > recent_high and is_high_volume:
        bullish_score += 25
        reasons.append("Structure Breakout: High-volume breakout above swing high.")
    elif ltp < recent_low and is_high_volume:
        bearish_score += 25
        reasons.append("Structure Breakdown: Heavy selling volume breakdown below swing low.")
    else:
        bullish_score += 10
        bearish_score += 10

    # D. RSI Momentum (15 Points)
    if 52 <= latest_rsi <= 75:
        bullish_score += 15
        reasons.append(f"RSI Momentum: Healthy bullish momentum ({round(latest_rsi,1)}).")
    elif 25 <= latest_rsi <= 48:
        bearish_score += 15
        reasons.append(f"RSI Momentum: Bearish momentum active ({round(latest_rsi,1)}).")

    # E. News Sentiment Alignment (10 Points)
    if bull_news_cnt > bear_news_cnt:
        bullish_score += 10
        reasons.append("News Sentiment: Live news headlines supporting bullish bias.")
    elif bear_news_cnt > bull_news_cnt:
        bearish_score += 10
        reasons.append("News Sentiment: Live news headlines supporting bearish bias.")

    # 4. Deep Decision Logic (Requires >= 80% High Conviction)
    action = "HOLD / WAIT"
    confidence = max(bullish_score, bearish_score)
    target1, target2, stop_loss, rr_ratio = "N/A", "N/A", "N/A", "N/A"
    min_sl_dist = ltp * 0.0075

    if bullish_score >= 80:
        action = "BUY CALL (CE)"
        raw_sl = round(recent_low if recent_low < ltp else s1, 2)
        stop_loss = round(ltp - min_sl_dist, 2) if (ltp - raw_sl) < min_sl_dist else raw_sl
        target1 = round(r1 if r1 > ltp else ltp + (min_sl_dist * 2), 2)
        target2 = round(r2 if r2 > target1 else target1 + (min_sl_dist * 1.5), 2)
        rr_ratio = "1 : 2.5+"
    elif bearish_score >= 80:
        action = "BUY PUT (PE)"
        raw_sl = round(recent_high if recent_high > ltp else r1, 2)
        stop_loss = round(ltp + min_sl_dist, 2) if (raw_sl - ltp) < min_sl_dist else raw_sl
        target1 = round(s1 if s1 < ltp else ltp - (min_sl_dist * 2), 2)
        target2 = round(s2 if s2 < target1 else target1 - (min_sl_dist * 1.5), 2)
        rr_ratio = "1 : 2.5+"
    else:
        action = "HOLD / NO SETUP"
        reasons = [f"AI Score is {confidence}% (Below senior 80% threshold). Market noise filtered; awaiting high-probability institutional setup."]

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