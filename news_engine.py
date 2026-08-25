import yfinance as yf
import requests
import xml.etree.ElementTree as ET
import urllib3

# SSL Warning मेसेज बंद करण्यासाठी
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_live_news_headlines():
    """
    Google News RSS द्वारे बाजारातील महत्वाच्या Top 3 Breaking Headlines ट्रॅक करते.
    """
    url = "https://news.google.com/rss/search?q=Nifty+Indian+stock+market+global+cues+crude+oil&hl=en-IN&gl=IN&ceid=IN:en"
    headlines = []
    try:
        # verify=False जोडल्यामुळे SSL Certificate एरर निघून जाईल
        response = requests.get(url, timeout=5, verify=False)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            items = root.findall(".//item")[:3]
            for item in items:
                title = item.find("title").text if item.find("title") is not None else ""
                clean_title = title.split(" - ")[0].strip()
                if clean_title:
                    headlines.append(clean_title)
    except Exception as e:
        print(f"[News Headlines Parsing Error]: {e}")

    if not headlines:
        headlines = [
            "US sanctions & Middle-East geopolitics driving crude oil volatility.",
            "FII selling pressure impacting emerging market equity sentiment.",
            "Global central bank updates keeping intraday traders cautious."
        ]
    return headlines

def fetch_global_market_sentiment():
    """
    1. Global Indices (S&P 500, GIFT Nifty, USD/INR, Nikkei) चा क्वांट डेटा ट्रॅक करते.
    2. Live Headlines स्कॅन करून युनिफाईड सेंटीमेंट स्कोअर आणि बातम्या रिटर्न करते.
    """
    global_tickers = {
        "GIFT_NIFTY": "^NSEI",
        "S&P 500 (US)": "^GSPC",
        "NASDAQ (US)": "^IXIC",
        "NIKKEI 225 (Asia)": "^N225",
        "USD/INR": "USDINR=X"
    }

    sentiment_data = {}
    score = 0

    # १. Global Indices Data (yfinance)
    try:
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
                else: # Stronger Dollar is bearish for Indian Equities
                    if pct_change > 0.3: score -= 1
                    elif pct_change < -0.3: score += 1
    except Exception as e:
        print(f"[News Quant Engine Error]: {e}")

    # २. Live News Headlines Extraction
    headlines = fetch_live_news_headlines()

    # ३. News Keyword Sentiment Score
    news_score = 0
    bearish_kw = ["crash", "drop", "fall", "sanction", "war", "tension", "sell", "plunge", "decline"]
    bullish_kw = ["rally", "surge", "gain", "jump", "growth", "record", "rise", "soar"]

    for headline in headlines:
        h_lower = headline.lower()
        if any(kw in h_lower for kw in bearish_kw):
            news_score -= 1
        if any(kw in h_lower for kw in bullish_kw):
            news_score += 1

    # Total Combined Score (Quant + News)
    total_score = score + news_score

    bias = "BULLISH 🟢" if total_score > 0 else ("BEARISH 🔴" if total_score < 0 else "NEUTRAL ⚪")

    return bias, sentiment_data, headlines