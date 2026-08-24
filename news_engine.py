import yfinance as yf

def fetch_global_market_sentiment():
    """Scans US, Asian, Forex, and GIFT Nifty markets for overnight bias."""
    try:
        global_tickers = {
            "GIFT_NIFTY": "^NSEI",
            "S&P 500 (US)": "^GSPC",
            "NASDAQ (US)": "^IXIC",
            "NIKKEI 225 (Asia)": "^N225",
            "USD/INR": "USDINR=X"
        }
        
        sentiment_data = {}
        score = 0
        
        for name, symbol in global_tickers.items():
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                curr_price = hist['Close'].iloc[-1]
                pct_change = ((curr_price - prev_close) / prev_close) * 100
                sentiment_data[name] = round(pct_change, 2)
                
                # Scoring logic
                if name != "USD/INR":
                    if pct_change > 0.5: score += 1
                    elif pct_change < -0.5: score -= 1
                else: # Stronger Dollar is usually bearish for Indian Equities
                    if pct_change > 0.3: score -= 1
                    elif pct_change < -0.3: score += 1

        bias = "BULLISH 🟢" if score > 0 else ("BEARISH 🔴" if score < 0 else "NEUTRAL ⚪")
        return bias, sentiment_data
    except Exception as e:
        print(f"[News Engine Error]: {e}")
        return "NEUTRAL ⚪", {}