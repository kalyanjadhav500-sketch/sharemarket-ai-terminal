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
    
    # 1. Technical Indicators
    df['EMA_9'] = close_series.ewm(span=9, adjust=False).mean()
    df['EMA_21'] = close_series.ewm(span=21, adjust=False).mean()
    df['RSI'] = calculate_rsi(close_series, 14)
    
    # 🛡️ SAFE VWAP CALCULATION (Fixes NaN for Index & Angel Broking Ticks)
    typical_price = (high_series + low_series + close_series) / 3
    if volume_series.sum() == 0 or volume_series.isna().all():
        df['VWAP'] = typical_price.ewm(span=14, adjust=False).mean()
        latest_vwap = df['VWAP'].iloc[-1]
    else:
        df['VWAP'] = (typical_price * volume_series).cumsum() / (volume_series.cumsum() + 1e-9)
        latest_vwap = df['VWAP'].iloc[-1]
        
    # Final Fallback Safeguard against NaN
    high = high_series.max()
    low = low_series.min()
    close = close_series.iloc[-1]
    pivot = (high + low + close) / 3

    if np.isnan(latest_vwap) or latest_vwap == 0:
        latest_vwap = pivot

    latest_ema9 = df['EMA_9'].iloc[-1]
    latest_ema21 = df['EMA_21'].iloc[-1]
    latest_rsi = df['RSI'].iloc[-1]
    
    avg_vol = volume_series.rolling(window=15).mean().iloc[-1]
    curr_vol = volume_series.iloc[-1]
    is_high_volume = curr_vol > (avg_vol * 1.15) if (not np.isnan(avg_vol) and avg_vol > 0) else True

    recent_high = high_series.iloc[-10:-1].max()
    recent_low = low_series.iloc[-10:-1].min()

    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)

    # 2. Live News Parsing & Sentiment
    news_text = " ".join(news_headlines).lower() if news_headlines else ""
    bullish_keywords = ["gain", "bull", "surge", "high", "growth", "buy", "profit", "positive", "up", "rally"]
    bearish_keywords = ["fall", "bear", "drop", "low", "loss", "sell", "down", "warning", "negative", "plummet"]
    
    bull_news_cnt = sum(1 for kw in bullish_keywords if kw in news_text)
    bear_news_cnt = sum(1 for kw in bearish_keywords if kw in news_text)

    # 3. Institutional Confluence Scoring (100 Points Scale)
    bullish_score = 0
    bearish_score = 0
    reasons = []

    if latest_ema9 > latest_ema21 and ltp > latest_ema9:
        bullish_score += 25
        reasons.append("Trend Confluence: 9 EMA > 21 EMA with active buying momentum.")
    elif latest_ema9 < latest_ema21 and ltp < latest_ema9:
        bearish_score += 25
        reasons.append("Trend Confluence: 9 EMA < 21 EMA with active selling momentum.")

    if ltp > latest_vwap:
        bullish_score += 25
        reasons.append(f"VWAP Institutional Support: Price (₹{round(ltp,2)}) sustained above VWAP (₹{round(latest_vwap,2)}).")
    else:
        bearish_score += 25
        reasons.append(f"VWAP Institutional Resistance: Price (₹{round(ltp,2)}) trading below VWAP (₹{round(latest_vwap,2)}).")

    if ltp > recent_high and is_high_volume:
        bullish_score += 25
        reasons.append("Structure Breakout: High-volume breakout above swing high.")
    elif ltp < recent_low and is_high_volume:
        bearish_score += 25
        reasons.append("Structure Breakdown: Heavy volume breakdown below swing low.")
    else:
        bullish_score += 10
        bearish_score += 10

    if 52 <= latest_rsi <= 75:
        bullish_score += 15
        reasons.append(f"RSI Momentum: Strong bullish setup ({round(latest_rsi,1)}).")
    elif 25 <= latest_rsi <= 48:
        bearish_score += 15
        reasons.append(f"RSI Momentum: Strong bearish setup ({round(latest_rsi,1)}).")

    if bull_news_cnt > bear_news_cnt:
        bullish_score += 10
        reasons.append("News Sentiment: Positive live news flow supporting trade.")
    elif bear_news_cnt > bull_news_cnt:
        bearish_score += 10
        reasons.append("News Sentiment: Negative live news flow supporting short bias.")

    # 4. Deep Decision Logic (Requires >= 80% Institutional Confluence)
    action = "HOLD / WAIT"
    confidence = max(bullish_score, bearish_score)
    target1, target2, stop_loss, rr_ratio = "N/A", "N/A", "N/A", "N/A"
    min_sl_dist = ltp * 0.0075

    if bullish_score >= 80:
        action = "BUY CALL (CE)"
        raw_sl = round(recent_low if recent_low < ltp else s1, 2)
        stop_loss = round(ltp - min_sl_dist, 2) if (ltp - raw_sl) < min_sl_dist else raw_sl
        target1 = round(ltp + (min_sl_dist * 2.0), 2)
        target2 = round(ltp + (min_sl_dist * 3.5), 2)
        rr_ratio = "1 : 2.5+"
    elif bearish_score >= 80:
        action = "BUY PUT (PE)"
        raw_sl = round(recent_high if recent_high > ltp else r1, 2)
        stop_loss = round(ltp + min_sl_dist, 2) if (raw_sl - ltp) < min_sl_dist else raw_sl
        target1 = round(ltp - (min_sl_dist * 2.0), 2)
        target2 = round(ltp - (min_sl_dist * 3.5), 2)
        rr_ratio = "1 : 2.5+"
    else:
        action = "HOLD / NO SETUP"
        reasons = [f"AI Score is {confidence}% (Below senior 80% threshold). Awaiting high-probability setup."]

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