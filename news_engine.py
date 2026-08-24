import requests
import xml.etree.ElementTree as ET
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_market_news():
    url = "https://news.google.com/rss/search?q=Indian+Stock+Market+NSE+NIFTY&hl=en-IN&gl=IN&ceid=IN:en"
    headlines = []
    try:
        r = requests.get(url, timeout=8, verify=False)  # SSL एरर फिक्स
        if r.ok:
            root = ET.fromstring(r.text)
            for item in root.findall('.//item')[:3]:
                title = item.find('title').text if item.find('title') is not None else ""
                headlines.append(title.split(" - ")[0])
    except Exception:
        headlines = ["Market tracking active indicators and moving averages."]
    return headlines if headlines else ["Market consolidation phase observed."]