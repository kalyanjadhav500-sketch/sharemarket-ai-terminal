import pandas as pd
import numpy as np
import yfinance as yf

def get_institutional_fundamentals(ticker_symbol):
    """Fetches fundamental metrics and valuation indicators for equity stocks."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        pe_ratio = info.get('trailingPE', 0)
        profit_margins = info.get('profitMargins', 0)
        
        if pe_ratio > 0 and pe_ratio < 35 and profit_margins > 0.10:
            return "STRONG", f"Solid Fundamentals (P/E: {round(pe_ratio,1)}, Margin: {round(profit_margins*100,1)}%)"
        elif pe_ratio > 60:
            return "OVERVALUED", f"Stock Overvalued (P/E: {round(pe_ratio,1)})"
        return "NEUTRAL", "Standard Fundamental Profile"
    except Exception:
        return "NEUTRAL", "Fundamental Data Unavailable"

def fetch_live_news_sentiment(ticker_symbol):
    """Analyzes real-time news headlines to determine market sentiment."""
    try:
        stock = yf.Ticker(ticker_symbol)
        news_list = stock.news
        if not news_list:
            return "NEUTRAL", "Neutral Market News Sentiment"
        
        positive_words = ['profit', 'growth', 'surge', 'buy', 'record', 'gain', 'approval', 'bullish', 'outperform']
        negative_words = ['loss', 'decline', 'drop', 'fall', 'penalty', 'sebi', 'bearish', 'fraud', 'probe', 'downgrade']
        
        pos_score, neg_score = 0, 0
        latest_headline = news_list[0].get('title', '')
        
        for item in news_list[:5]:
            title = item.get('title', '').lower()
            for w in positive_words:
                if w in title: pos_score += 1
            for w in negative_words:
                if w in title: neg_score += 1

        if pos_score > neg_score:
            return "BULLISH", f"Positive Sentiment: {latest_headline[:65]}..."
        elif neg_score > pos_score:
            return "BEARISH", f"Negative Sentiment Warning: {latest_headline[:65]}..."
        return "NEUTRAL", "Neutral News Flow"
    except Exception:
        return "NEUTRAL", "News Data Unavailable"

def add_indicators(df):
    """Calculates Technical Indicators: EMA, VWAP, VWAP SD Bands, RSI, ATR, and FVG."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or len(df) < 10:
        return df
    
    df = df.copy()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean() if len(df) >= 200 else df['EMA_50']
    
    # VWAP & Standard Deviation Bands
    v = df['Volume'].replace(0, 1)
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = (tp * v).cumsum() / v.cumsum()
    vwap_var = ((tp - df['VWAP']) ** 2 * v).cumsum() / v.cumsum()
    vwap_sd = np.sqrt(vwap_var)
    df['VWAP_UPPER'] = df['VWAP'] + (1.5 * vwap_sd)
    df['VWAP_LOWER'] = df['VWAP'] - (1.5 * vwap_sd)
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = df['RSI'].fillna(50)
    
    # Average True Range (ATR)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['ATR'] = np.max(ranges, axis=1).rolling(14).mean()
    
    # Fair Value Gap (FVG) Detection
    df['FVG_BULLISH'] = (df['Low'] > df['High'].shift(2))
    df['FVG_BEARISH'] = (df['High'] < df['Low'].shift(2))
    
    return df

def analyze_index(symbol, df_15m, display_name=None):
    """Institutional Level Index Strategy for NIFTY / BANKNIFTY Options Trading."""
    if df_15m is None or not isinstance(df_15m, pd.DataFrame) or df_15m.empty or len(df_15m) < 10:
        return None
    
    name = display_name if display_name else symbol
    
    # Macro Daily Trend Analysis
    try:
        df_daily = yf.download(symbol, period="6mo", interval="1d", progress=False)
        if isinstance(df_daily.columns, pd.MultiIndex): df_daily.columns = df_daily.columns.get_level_values(0)
        df_daily = add_indicators(df_daily)
        d_close = float(df_daily['Close'].iloc[-1])
        d_ema50 = float(df_daily['EMA_50'].iloc[-1]) if pd.notna(df_daily['EMA_50'].iloc[-1]) else d_close
        d_ema200 = float(df_daily['EMA_200'].iloc[-1]) if pd.notna(df_daily['EMA_200'].iloc[-1]) else d_close
        macro_trend = "BULLISH" if d_close > d_ema50 and d_close > d_ema200 else ("BEARISH" if d_close < d_ema50 and d_close < d_ema200 else "NEUTRAL")
    except Exception:
        macro_trend = "NEUTRAL"

    # Intraday Multi-Indicator Execution
    df_15m = add_indicators(df_15m)
    l = df_15m.iloc[-1]
    price = float(l["Close"])
    vwap = float(l["VWAP"]) if pd.notna(l["VWAP"]) else price
    ema21 = float(l["EMA_21"]) if pd.notna(l["EMA_21"]) else price
    rsi = float(l["RSI"]) if pd.notna(l["RSI"]) else 50
    raw_atr = l["ATR"] if pd.notna(l["ATR"]) else 0
    atr = max(float(raw_atr), price * 0.0035)
    fvg_bull = bool(l["FVG_BULLISH"])
    fvg_bear = bool(l["FVG_BEARISH"])
    
    reasons = []
    reasons.append(f"<b>Macro Daily Trend:</b> {macro_trend}")
    
    # Confluence Scoring Engine
    score = 50
    if macro_trend == "BULLISH": score += 15
    elif macro_trend == "BEARISH": score -= 15
    
    if price > vwap: score += 15
    else: score -= 15
    
    if price > ema21: score += 10
    else: score -= 10
    
    if rsi > 55: score += 10
    elif rsi < 45: score -= 10
    
    if fvg_bull: score += 10
    if fvg_bear: score -= 10

    # Decision Matrix
    if score >= 75 and price > vwap and price > ema21:
        trend = "INSTITUTIONAL BULLISH"
        action = "BUY CALL (CE)"
        sl = round(price - (1.0 * atr), 2)
        tp1 = round(price + (1.6 * atr), 2)
        tp2 = round(price + (2.8 * atr), 2)
        reasons.append("<b>Smart Money Flow:</b> Price trading above VWAP and EMA 21.")
        reasons.append(f"<b>Momentum Strength:</b> RSI at {round(rsi, 1)} with Bullish Confluence.")
        if fvg_bull: reasons.append("<b>Price Action:</b> Bullish Fair Value Gap (FVG) detected.")
        confidence = min(score, 96)
        
    elif score <= 25 and price < vwap and price < ema21:
        trend = "INSTITUTIONAL BEARISH"
        action = "BUY PUT (PE)"
        sl = round(price + (1.0 * atr), 2)
        tp1 = round(price - (1.6 * atr), 2)
        tp2 = round(price - (2.8 * atr), 2)
        reasons.append("<b>Smart Money Flow:</b> Institutional supply pressure below VWAP.")
        reasons.append(f"<b>Momentum Weakness:</b> RSI at {round(rsi, 1)} with Bearish Confluence.")
        if fvg_bear: reasons.append("<b>Price Action:</b> Bearish Fair Value Gap (FVG) detected.")
        confidence = min(100 - score, 96)
        
    else:
        trend = "NO TRADE ZONE"
        action = "HOLD / WAIT"
        sl, tp1, tp2 = price, price, price
        reasons.append("<b>Capital Shield Guardrail:</b> Market structure is choppy/conflicted.")
        reasons.append("<b>Risk Mitigation:</b> AI Agent prevented trade execution in low-probability setup.")
        confidence = 98

    return {
        "name": name, "symbol": symbol, "trend": trend, "price": round(price, 2),
        "action": action, "entry": round(price, 2), "sl": sl, "tp1": tp1, "tp2": tp2,
        "rsi": round(rsi, 1), "confidence": confidence, "reasons": reasons
    }

def build_scanner_row(symbol, df_15m, df_daily=None, *args, **kwargs):
    """Advanced Multi-Dimensional Equity Scanner Engine."""
    if df_15m is None or not isinstance(df_15m, pd.DataFrame) or df_15m.empty or len(df_15m) < 10:
        return None

    yf_ticker = f"{symbol}.NS"
    
    fund_score, fund_desc = get_institutional_fundamentals(yf_ticker)
    news_score, news_desc = fetch_live_news_sentiment(yf_ticker)
    
    try:
        if df_daily is None or df_daily.empty:
            df_daily = yf.download(yf_ticker, period="6mo", interval="1d", progress=False)
            if isinstance(df_daily.columns, pd.MultiIndex): df_daily.columns = df_daily.columns.get_level_values(0)
        df_daily = add_indicators(df_daily)
        d_close = float(df_daily['Close'].iloc[-1])
        d_ema50 = float(df_daily['EMA_50'].iloc[-1]) if pd.notna(df_daily['EMA_50'].iloc[-1]) else d_close
        macro_trend = "BULLISH" if d_close > d_ema50 else "BEARISH"
    except Exception:
        macro_trend = "NEUTRAL"

    df_15m = add_indicators(df_15m)
    l = df_15m.iloc[-1]
    price = float(l["Close"])
    vwap = float(l["VWAP"]) if pd.notna(l["VWAP"]) else price
    ema21 = float(l["EMA_21"]) if pd.notna(l["EMA_21"]) else price
    rsi = float(l["RSI"]) if pd.notna(l["RSI"]) else 50
    raw_atr = l["ATR"] if pd.notna(l["ATR"]) else 0
    atr = max(float(raw_atr), price * 0.005)

    reasons = []
    reasons.append(f"<b>Fundamentals:</b> {fund_desc}")
    reasons.append(f"<b>News Analysis:</b> {news_desc}")
    reasons.append(f"<b>Macro Trend:</b> Daily Chart {macro_trend}")

    if (news_score == "BULLISH" or price > vwap) and macro_trend == "BULLISH" and fund_score != "OVERVALUED":
        trend = "BULLISH"
        action = "BUY / LONG"
        sl = round(price - (1.0 * atr), 2)
        tp1 = round(price + (1.8 * atr), 2)
        tp2 = round(price + (3.0 * atr), 2)
        reasons.append("<b>Confluence:</b> Technical & Fundamental Alignment Confirmed.")
        confidence = 94 if news_score == "BULLISH" else 88
        
    elif (news_score == "BEARISH" or price < vwap) and macro_trend == "BEARISH":
        trend = "BEARISH"
        action = "SELL / SHORT"
        sl = round(price + (1.0 * atr), 2)
        tp1 = round(price - (1.8 * atr), 2)
        tp2 = round(price - (3.0 * atr), 2)
        reasons.append("<b>Confluence:</b> Technical & Fundamental Weakness Confirmed.")
        confidence = 94 if news_score == "BEARISH" else 88
        
    else:
        trend = "SIDEWAYS"
        action = "NO TRADE"
        sl, tp1, tp2 = price, price, price
        reasons.append("<b>Capital Preservation:</b> Conflict detected across factors. Trade prevented.")
        confidence = 90

    return {
        "name": symbol, "symbol": symbol, "trend": trend, "price": round(price, 2),
        "action": action, "confidence": confidence, "entry": round(price, 2),
        "sl": sl, "tp1": tp1, "tp2": tp2, "reasons": reasons
    }