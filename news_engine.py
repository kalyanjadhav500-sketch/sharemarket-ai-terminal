import urllib.parse
import xml.etree.ElementTree as ET
import requests

def fetch_stock_news_sentiment(symbol):
    """२४ तास थेट बातम्या स्कॅन करून सेंटीमेंट स्कोर तयार करणे"""
    clean_sym = symbol.replace(".NS", "")
    query = f"{clean_sym} share news India"
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    positive_words = ['growth', 'profit', 'buy', 'bullish', 'up', 'gain', 'high', 'partnership', 'approval', 'record']
    negative_words = ['loss', 'fall', 'bearish', 'down', 'sell', 'drop', 'raid', 'penalty', 'decline', 'investigation']
    
    score = 0
    headlines = []
    
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall('.//item')[:5]:
                title = item.find('title').text
                headlines.append(title)
                title_lower = title.lower()
                
                for p in positive_words:
                    if p in title_lower: score += 10
                for n in negative_words:
                    if n in title_lower: score -= 10
    except Exception:
        pass
        
    sentiment = "BULLISH" if score > 10 else ("BEARISH" if score < -10 else "NEUTRAL")
    return {"sentiment": sentiment, "score": score, "headlines": headlines[:3]}

def fetch_market_news():
    """auto_telegram_scanner साठी मार्केट न्यूज रॅपर फंक्शन"""
    return fetch_stock_news_sentiment("NIFTY 50")