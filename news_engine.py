import urllib.parse
import xml.etree.ElementTree as ET
import requests

def fetch_market_news(query="NIFTY 50 Stock Market India"):
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            headlines = []
            for item in items[:5]:
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                headlines.append({"title": title, "link": link})
            return headlines
    except Exception as e:
        print(f"[NEWS ERROR] {e}")
    return []

def get_news_sentiment(headlines):
    bullish_keywords = ["surge", "rally", "profit", "bullish", "high", "gain", "record", "growth"]
    bearish_keywords = ["fall", "drop", "plunge", "bearish", "loss", "decline", "crash", "down"]
    
    score = 0
    for item in headlines:
        text = item["title"].lower()
        score += sum(1 for w in bullish_keywords if w in text)
        score -= sum(1 for w in bearish_keywords if w in text)
        
    if score > 0:
        return "BULLISH 🟢"
    elif score < 0:
        return "BEARISH 🔴"
    return "NEUTRAL 🟡"