"""Compatibility layer for the original advanced_features.py.

All secrets are read from environment variables. No paid service is required.
"""
from telegram_alerts import send_telegram_signal
import requests
import pandas as pd
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import os

def send_rich_telegram_card(symbol, signal_type, entry_price, target1, target2, stop_loss, risk_reward):
    row={"symbol":symbol,"action":signal_type.upper(),"confidence":0,"bull_score":0,"bear_score":0,
         "entry_low":entry_price,"entry_high":entry_price,"sl":stop_loss,"tp1":target1,"tp2":target2,
         "rr":risk_reward,"regime":"N/A","sector":"N/A","smart_money":0,"rel_volume":0}
    ok,_=send_telegram_signal(row)
    return ok

def generate_and_send_chart(symbol, prices_df):
    token=os.getenv("TELEGRAM_BOT_TOKEN",""); chat=os.getenv("TELEGRAM_CHAT_ID","")
    if not token or not chat or prices_df.empty:
        return False
    filename="temp_chart.png"
    try:
        plt.figure(figsize=(9,4))
        plt.plot(prices_df["Close"],label="Close")
        if "VWAP" in prices_df.columns: plt.plot(prices_df["VWAP"],label="VWAP")
        plt.title(f"{symbol} Quant Chart"); plt.grid(alpha=.2); plt.legend()
        plt.tight_layout(); plt.savefig(filename,dpi=120); plt.close()
        with open(filename,"rb") as photo:
            r=requests.post(f"https://api.telegram.org/bot{token}/sendPhoto",
                            data={"chat_id":chat,"caption":f"{symbol} Quant Chart"},
                            files={"photo":photo},timeout=20)
        return r.ok
    except Exception:
        return False
    finally:
        if os.path.exists(filename): os.remove(filename)

def get_market_news_sentiment():
    url="https://news.google.com/rss/search?q=Indian+Stock+Market+Nifty&hl=en-IN&gl=IN&ceid=IN:en"
    positive={"rally","growth","gain","surge","profit","positive","breakout","upgrade"}
    negative={"fall","bear","crash","drop","loss","decline","negative","inflation","fear","downgrade"}
    try:
        r=requests.get(url,timeout=10)
        soup=BeautifulSoup(r.content,"xml")
        items=soup.find_all("item",limit=10)
        headlines=[i.title.text for i in items if i.title]
        pos=sum(w in h.lower() for h in headlines for w in positive)
        neg=sum(w in h.lower() for h in headlines for w in negative)
        return {"sentiment":"BULLISH" if pos>neg else "BEARISH" if neg>pos else "NEUTRAL",
                "positive_score":pos,"negative_score":neg,"top_headlines":headlines[:5]}
    except Exception:
        return None
