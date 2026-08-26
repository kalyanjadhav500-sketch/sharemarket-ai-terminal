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

def analyze_option_chain_oi(pcr_value, ltp, hard_resistance=None, hard_support=None):
    """
    Evaluates Institutional Sentiment via Option Chain PCR & Open Interest (OI)
    """
    oi_bullish = 0
    oi_bearish = 0
    reasons = []

    # PCR Scoring Logic
    if pcr_value >= 1.2:
        oi_bullish += 15
        reasons.append(f"Option Chain: High PCR ({pcr_value}) - Institutional Put Writing (Bullish).")
    elif pcr_value <= 0.7:
        oi_bearish += 15
        reasons.append(f"Option Chain: Low PCR ({pcr_value}) - Institutional Call Writing (Bearish).")
    else:
        reasons.append(f"Option Chain: Neutral PCR ({pcr_value}).")

    # Hard Resistance & Support Wall Checks
    near_resistance = False
    near_support = False

    if hard_resistance and abs(hard_resistance - ltp) <= 50:
        near_resistance = True
        reasons.append(f"⚠️ OI Alert: Price near Hard Resistance (Max Call OI Strike ₹{hard_resistance}).")

    if hard_support and abs(ltp - hard_support) <= 50:
        near_support = True
        reasons.append(f"⚠️ OI Alert: Price near Hard Support (Max Put OI Strike ₹{hard_support}).")

    return oi_bullish, oi_bearish, near_resistance, near_support, reasons


def analyze_institutional_matrix(
    symbol, 
    df_5m, 
    df_15m, 
    df_daily, 
    df_vix=None, 
    df_heavyweight=None, 
    pcr_value=1.0,
    hard_resistance=None,
    hard_support=None,
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

    # --- 1. Option Chain & PCR Analysis ---
    oi_bull, oi_bear, near_res, near_sup, oi_reasons = analyze_option_chain_oi(
        pcr_value, ltp, hard_resistance, hard_support
    )
    bullish_score += oi_bull
    bearish_score += oi_bear
    reasons.extend(oi_reasons)

    # --- 2. India VIX Risk Shield ---
    vix_val = df_vix['Close'].iloc[-1] if (df_vix is not None and not df_vix.empty) else 15.0
    if vix_val > 20:
        sl_atr_mult = 2.0
        reasons.append(f"India VIX Shield: High Volatility ({round(vix_val, 2)}). SL widened to 2.0x ATR.")
    elif vix_val < 11:
        sl_atr_mult = 1.2
        reasons.append(f"India VIX Shield: Low Volatility ({round(vix_val, 2)}). Tight SL active.")
    else:
        sl_atr_mult = 1.5

    # --- 3. Daily & Macro Trend Check (20 Points) ---
    pdh = df_daily['High'].iloc[-2] if len(df_daily) >= 2 else df_daily['High'].iloc[-1]
    pdl = df_daily['Low'].iloc[-2] if len(df_daily) >= 2 else df_daily['Low'].iloc[-1]
    daily_ema20 = df_daily['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
    
    if ltp > daily_ema20:
        bullish_score += 20
        reasons.append(f"Daily Macro: Trading above Daily 20 EMA (₹{round(daily_ema20, 2)}).")
    else:
        bearish_score += 20
        reasons.append(f"Daily Macro: Trading below Daily 20 EMA (₹{round(daily_ema20, 2)}).")

    # --- 4. Intraday 15-Min Momentum (20 Points) ---
    ema9_15m = df_15m['Close'].ewm(span=9, adjust=False).mean().iloc[-1]
    ema21_15m = df_15m['Close'].ewm(span=21, adjust=False).mean().iloc[-1]
    if ema9_15m > ema21_15m:
        bullish_score += 20
        reasons.append("15m Intraday: Bullish EMA Alignment (9 > 21).")
    else:
        bearish_score += 20
        reasons.append("15m Intraday: Bearish EMA Alignment (9 < 21).")

    # --- 5. Heavyweight Stock Sync Check (15 Points) ---
    if df_heavyweight is not None and not df_heavyweight.empty:
        hw_close = df_heavyweight['Close']
        hw_change = ((hw_close.iloc[-1] - hw_close.iloc[-2]) / hw_close.iloc[-2]) * 100 if len(hw_close) >= 2 else 0
        if hw_change > 0.2:
            bullish_score += 15
            reasons.append(f"Heavyweight Sync: Sector Leader UP (+{round(hw_change,2)}%).")
        elif hw_change < -0.2:
            bearish_score += 15
            reasons.append(f"Heavyweight Sync: Sector Leader DOWN ({round(hw_change,2)}%).")

    # --- 6. Execution Timeframe 5-Min (30 Points) ---
    close_5m = df_5m['Close']
    high_5m = df_5m['High']
    low_5m = df_5m['Low']
    vol_5m = df_5m['Volume']

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
        bullish_score += 15
        reasons.append(f"VWAP Check: Price above VWAP (₹{round(latest_vwap, 2)}).")
    else:
        bearish_score += 15
        reasons.append(f"VWAP Check: Price below VWAP (₹{round(latest_vwap, 2)}).")

    if 53 <= latest_rsi <= 75:
        bullish_score += 15
        reasons.append(f"RSI Momentum: Bullish Strength ({round(latest_rsi, 1)}).")
    elif 25 <= latest_rsi <= 47:
        bearish_score += 15
        reasons.append(f"RSI Momentum: Bearish Strength ({round(latest_rsi, 1)}).")

    # --- 7. Execution Decision (Threshold >= 85%) ---
    action = "HOLD / NO SETUP"
    confidence = max(bullish_score, bearish_score)
    target1, target2, stop_loss, rr_ratio = "N/A", "N/A", "N/A", "N/A"

    # HARD FILTER: Don't buy Call right into Hard Resistance; Don't buy Put into Hard Support!
    if bullish_score >= 85 and not near_res:
        action = "BUY CALL (CE)"
        stop_loss = round(ltp - (sl_atr_mult * atr), 2)
        target1 = round(ltp + (2.0 * atr), 2)
        target2 = round(ltp + (3.5 * atr), 2)
        rr_ratio = f"1 : {round(2.0/sl_atr_mult, 1)}+ (ATR Shield)"
    elif bearish_score >= 85 and not near_sup:
        action = "BUY PUT (PE)"
        stop_loss = round(ltp + (sl_atr_mult * atr), 2)
        target1 = round(ltp - (2.0 * atr), 2)
        target2 = round(ltp - (3.5 * atr), 2)
        rr_ratio = f"1 : {round(2.0/sl_atr_mult, 1)}+ (ATR Shield)"
    elif near_res or near_sup:
        reasons.append("⛔ TRADE REJECTED: Price near Hard Institutional Support/Resistance wall!")

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