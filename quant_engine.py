import pandas as pd
import numpy as np

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(period).mean().iloc[-1]
    return atr if (not np.isnan(atr) and atr > 0) else (df['Close'].iloc[-1] * 0.005)

def analyze_institutional_matrix(
    symbol, 
    df_5m, 
    df_15m, 
    df_daily, 
    df_vix=None, 
    df_heavyweight=None, 
    display_name="ASSET", 
    tick_data=None, 
    news_headlines=None
):
    if df_5m.empty or len(df_5m) < 15:
        return None

    ltp = tick_data.get("ltp", df_5m['Close'].iloc[-1]) if tick_data else df_5m['Close'].iloc[-1]
    reasons = []
    bullish_score = 0
    bearish_score = 0

    # --- 1. India VIX Volatility Adjustment ---
    vix_val = df_vix['Close'].iloc[-1] if (df_vix is not None and not df_vix.empty) else 15.0
    if vix_val > 20:
        sl_atr_mult = 2.0  # High Volatility -> Wider SL to prevent spike hits
        reasons.append(f"India VIX Alert: High Volatility ({round(vix_val, 2)}). Dynamic SL widened to 2.0x ATR.")
    elif vix_val < 11:
        sl_atr_mult = 1.2  # Low Volatility -> Tight SL
        reasons.append(f"India VIX Alert: Low Volatility ({round(vix_val, 2)}). Tight SL active.")
    else:
        sl_atr_mult = 1.5

    # --- 2. Daily & Macro Trend Check (20 Points) ---
    pdh = df_daily['High'].iloc[-2] if len(df_daily) >= 2 else df_daily['High'].iloc[-1]
    pdl = df_daily['Low'].iloc[-2] if len(df_daily) >= 2 else df_daily['Low'].iloc[-1]
    daily_ema20 = df_daily['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
    
    if ltp > daily_ema20:
        bullish_score += 20
        reasons.append(f"Daily Macro: Above Daily 20 EMA (₹{round(daily_ema20, 2)}).")
    else:
        bearish_score += 20
        reasons.append(f"Daily Macro: Below Daily 20 EMA (₹{round(daily_ema20, 2)}).")

    # --- 3. Intraday 15-Min Momentum (20 Points) ---
    ema9_15m = df_15m['Close'].ewm(span=9, adjust=False).mean().iloc[-1]
    ema21_15m = df_15m['Close'].ewm(span=21, adjust=False).mean().iloc[-1]
    if ema9_15m > ema21_15m:
        bullish_score += 20
        reasons.append("15m Trend: 9 EMA > 21 EMA Bullish Alignment.")
    else:
        bearish_score += 20
        reasons.append("15m Trend: 9 EMA < 21 EMA Bearish Alignment.")

    # --- 4. Heavyweight Stock Sync Check (15 Points) ---
    if df_heavyweight is not None and not df_heavyweight.empty:
        hw_close = df_heavyweight['Close']
        hw_change = ((hw_close.iloc[-1] - hw_close.iloc[-2]) / hw_close.iloc[-2]) * 100 if len(hw_close) >= 2 else 0
        if hw_change > 0.2:
            bullish_score += 15
            reasons.append(f"Heavyweight Sync: Sector Leader is UP (+{round(hw_change,2)}%).")
        elif hw_change < -0.2:
            bearish_score += 15
            reasons.append(f"Heavyweight Sync: Sector Leader is DOWN ({round(hw_change,2)}%).")

    # --- 5. Execution Timeframe 5-Min (VWAP, RSI, Structure) (45 Points) ---
    close_5m = df_5m['Close']
    high_5m = df_5m['High']
    low_5m = df_5m['Low']
    vol_5m = df_5m['Volume']

    df_5m['EMA_9'] = close_5m.ewm(span=9, adjust=False).mean()
    df_5m['EMA_21'] = close_5m.ewm(span=21, adjust=False).mean()
    df_5m['RSI'] = calculate_rsi(close_5m, 14)
    atr = calculate_atr(df_5m, 14)

    typical_price = (high_5m + low_5m + close_5m) / 3
    if vol_5m.sum() == 0 or vol_5m.isna().all():
        df_5m['VWAP'] = typical_price.ewm(span=14, adjust=False).mean()
    else:
        df_5m['VWAP'] = (typical_price * vol_5m).cumsum() / (vol_5m.cumsum() + 1e-9)

    latest_vwap = df_5m['VWAP'].iloc[-1]
    pivot = (high_5m.max() + low_5m.min() + close_5m.iloc[-1]) / 3
    if np.isnan(latest_vwap) or latest_vwap == 0:
        latest_vwap = pivot

    latest_rsi = df_5m['RSI'].iloc[-1]
    recent_high = high_5m.iloc[-10:-1].max()
    recent_low = low_5m.iloc[-10:-1].min()

    if ltp > latest_vwap:
        bullish_score += 20
        reasons.append(f"VWAP Level: Price trading above Institutional VWAP (₹{round(latest_vwap, 2)}).")
    else:
        bearish_score += 20
        reasons.append(f"VWAP Level: Price trading below Institutional VWAP (₹{round(latest_vwap, 2)}).")

    if ltp > recent_high or ltp > pdh:
        bullish_score += 15
        reasons.append("Structure: High Breakout confirmed.")
    elif ltp < recent_low or ltp < pdl:
        bearish_score += 15
        reasons.append("Structure: Low Breakdown confirmed.")

    if 53 <= latest_rsi <= 75:
        bullish_score += 10
        reasons.append(f"RSI Momentum: Bullish ({round(latest_rsi, 1)}).")
    elif 25 <= latest_rsi <= 47:
        bearish_score += 10
        reasons.append(f"RSI Momentum: Bearish ({round(latest_rsi, 1)}).")

    # --- 6. Execution Decision (Threshold >= 85) ---
    action = "HOLD / NO SETUP"
    confidence = max(bullish_score, bearish_score)
    target1, target2, stop_loss, rr_ratio = "N/A", "N/A", "N/A", "N/A"

    if bullish_score >= 85:
        action = "BUY CALL (CE)"
        stop_loss = round(ltp - (sl_atr_mult * atr), 2)
        target1 = round(ltp + (2.0 * atr), 2)
        target2 = round(ltp + (3.5 * atr), 2)
        rr_ratio = f"1 : {round(2.0/sl_atr_mult, 1)}+ (ATR Shield)"
    elif bearish_score >= 85:
        action = "BUY PUT (PE)"
        stop_loss = round(ltp + (sl_atr_mult * atr), 2)
        target1 = round(ltp - (2.0 * atr), 2)
        target2 = round(ltp - (3.5 * atr), 2)
        rr_ratio = f"1 : {round(2.0/sl_atr_mult, 1)}+ (ATR Shield)"
    else:
        reasons = [f"Institutional Score is {confidence}% (Needs 85%+ Multi-TF Alignment). Capital Protected."]

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
            "pdh": round(pdh, 2),
            "pdl": round(pdl, 2)
        },
        "reasons": reasons
    }