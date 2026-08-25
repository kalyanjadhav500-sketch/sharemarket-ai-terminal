import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import quote

def fetch_global_market_sentiment(symbol="MARKET"):
    try:
        # Clean symbol for search query
        clean_query = symbol.replace("^NSEBANK", "BANK NIFTY").replace("^NSEI", "NIFTY 50").replace(".NS", "")
        search_term = f"{clean_query} share news India"
        encoded_query = quote(search_term)
        
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=4).read()
        root = ET.fromstring(html)
        
        headlines = []
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text
            clean_title = title.split(" - ")[0] if " - " in title else title
            headlines.append(clean_title)
            
        details = {
            "Analyzed Asset": clean_query,
            "News Feed Status": "Live Dynamic RSS Stream",
            "Headlines Loaded": len(headlines)
        }
        
        return "ACTIVE", details, headlines if headlines else [f"No breaking updates for {clean_query} currently."]
    except Exception:
        return "NEUTRAL", {"Status": "Tracking"}, [f"Monitoring real-time news stream for {symbol}..."]