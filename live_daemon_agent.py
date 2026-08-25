import time
import datetime
import pytz
import yfinance as yf
import pandas as pd
from quant_engine import analyze_index, build_scanner_row
from news_engine import fetch_global_market_sentiment
from telegram_alerts import send_telegram_message, send_index_signal, send_top_stocks

# Clean Watchlist without delisted symbols
WATCHLIST_SECTORS = {
    "RELIANCE": "Energy", 
    "TCS": "IT", 
    "INFY": "IT",
    "HDFCBANK": "Banking", 
    "ICICIBANK": "Banking", 
    "SBIN": "Banking",
    "BHARTIARTL": "Telecom", 
    "TATASTEEL": "Metals"
}

ist = pytz.timezone('Asia/Kolkata')

# Global State & News Tracker
latest_index_signals = {}
latest_equity_signals = []
last_alert_sent = {}
pre_market_sent_date = None
current_news_sentiment = {"bias": "NEUTRAL", "details": {}, "headlines": []}

def is_market_hours():
    now = datetime.datetime.now(ist)
    if now.weekday() >= 5:
        return False
    market_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_start <= now <= market_end

def is_pre_market_time():
    now = datetime.datetime.now(ist)
    if now.weekday() >= 5:
        return False
    pre_start = now.replace(hour=8, minute=45, second=0, microsecond=0)
    pre_end = now.replace(hour=9, minute=14, second=0, microsecond=0)
    return pre_start <= now <= pre_end

def update_live_news_sentiment():
    """Continuously fetches real-time market sentiment and news breakdown."""
    global current_news_sentiment
    try:
        # news_engine मधील ३ ही व्हॅल्यूज अनपॅक (Unpack) केल्या आहेत
        bias, details, headlines = fetch_global_market_sentiment()
        current_news_sentiment = {
            "bias": bias, 
            "details": details, 
            "headlines": headlines
        }
        now_str = datetime.datetime.now(ist).strftime('%H:%M:%S')
        print(f"📰 [{now_str}] Live News & Headlines Updated: {bias}")
    except Exception as e:
        print(f"[News Fetch Error]: {e}")

def continuous_realtime_surveillance():
    """1-Minute High Frequency Tick Scan with Dynamic News Confluence."""
    global latest_index_signals, latest_equity_signals, last_alert_sent
    
    # 1. Index Surveillance (1-Minute Intervals for instant spike detection)
    for idx_symbol, idx_name in [("^NSEI", "NIFTY 50"), ("^NSEBANK", "BANK NIFTY")]:
        try:
            df_1m = yf.download(idx_symbol, period="1d", interval="1m", progress=False)
            if isinstance(df_1m.columns, pd.MultiIndex):
                df_1m.columns = df_1m.columns.get_level_values(0)
            
            if not df_1m.empty and len(df_1m) > 2:
                signal = analyze_index(idx_symbol, df_1m, display_name=idx_name)
                
                # Dynamic News Factor adjustment
                if signal:
                    signal['news_bias'] = current_news_sentiment['bias']
                    signal['news_headlines'] = current_news_sentiment.get('headlines', [])
                    latest_index_signals[idx_name] = signal
                    
                    # Instant Telegram Dispatch on High Confluence Action Signal
                    action = signal.get("action")
                    if action in ["BUY CALL (CE)", "BUY PUT (PE)"]:
                        last_time = last_alert_sent.get(idx_name)
                        now_time = time.time()
                        
                        # Prevent duplicate spam: trigger alert only if 5 mins passed or signal flipped
                        if not last_time or (now_time - last_time > 300):
                            send_index_signal(signal)
                            last_alert_sent[idx_name] = now_time
                            print(f"⚡ Instant Real-Time Alert Sent: {idx_name} -> {action}")
        except Exception as e:
            print(f"[Real-Time Watch Error - {idx_name}]: {e}")

    # 2. Equity Watchlist Scan (1-Min ticks)
    scanned_stocks = []
    for symbol, sector in WATCHLIST_SECTORS.items():
        try:
            df_1m = yf.download(f"{symbol}.NS", period="1d", interval="1m", progress=False)
            if isinstance(df_1m.columns, pd.MultiIndex):
                df_1m.columns = df_1m.columns.get_level_values(0)
            
            if not df_1m.empty and len(df_1m) > 2:
                row = build_scanner_row(symbol, df_1m, sector=sector)
                if row and row.get("action") in ["BUY / LONG", "SELL / SHORT"]:
                    row['news_bias'] = current_news_sentiment['bias']
                    scanned_stocks.append(row)
        except Exception as e:
            print(f"[Real-Time Watch Error - {symbol}]: {e}")

    if scanned_stocks:
        scanned_stocks.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        latest_equity_signals = scanned_stocks

def send_pre_market_briefing():
    """Morning Pre-Market News Briefing with Live Headlines."""
    global pre_market_sent_date
    today_date = datetime.datetime.now(ist).date()
    
    if pre_market_sent_date == today_date:
        return

    now_str = datetime.datetime.now(ist).strftime('%H:%M:%S')
    print(f"🌅 [{now_str}] Preparing Morning Pre-Market Briefing...")
    
    update_live_news_sentiment()
    bias = current_news_sentiment.get("bias", "NEUTRAL")
    details = current_news_sentiment.get("details", {})
    headlines = current_news_sentiment.get("headlines", [])
    
    details_formatted = "\n".join([f"• <b>{k}:</b> {v}%" if isinstance(v, (int, float)) else f"• <b>{k}:</b> {v}" for k, v in details.items()])
    headlines_formatted = "\n".join([f"📰 <i>{h}</i>" for h in headlines])
    
    msg = (
        f"🌅 <b>24x7 AI AGENT: PRE-MARKET & LIVE NEWS OUTLOOK</b>\n"
        f"───────────────\n"
        f"🎯 <b>Live Sentiment Bias:</b> {bias}\n"
        f"───────────────\n"
        f"📊 <b>Global Cues & Quant Indicators:</b>\n"
        f"{details_formatted}\n\n"
        f"🔥 <b>Top Real-Time Headlines:</b>\n"
        f"{headlines_formatted}\n\n"
        f"⚡ <i>Continuous 1-minute tick scanning & live news tracking active.</i>"
    )
    
    if send_telegram_message(msg):
        pre_market_sent_date = today_date
        print("[Pre-Market] Morning Briefing successfully delivered.")

def start_24x7_daemon():
    print("🤖 [STARTING CONTINUOUS 24/7 REAL-TIME QUANT & NEWS AI DAEMON] 🤖")
    
    news_timer = 0
    while True:
        try:
            # दर १५ मिनिटांनी लाईव्ह बातम्या व सेंटीमेंट अपडेट होतील
            if time.time() - news_timer > 900:
                update_live_news_sentiment()
                news_timer = time.time()

            # 1. LIVE MARKET HOURS (9:15 AM - 3:30 PM) -> Continuous 1-min Scans
            if is_market_hours():
                continuous_realtime_surveillance()
                time.sleep(10)  # दर १० सेकंदांनी रिअल-टाईम स्कॅनिंग
                
            # 2. PRE-MARKET HOURS (8:45 AM - 9:14 AM)
            elif is_pre_market_time():
                send_pre_market_briefing()
                time.sleep(60)

            # 3. OFF-MARKET HOURS (24x7 Background Monitoring)
            else:
                time.sleep(300) # ५ मिनिटांनी बॅकग्राऊंड न्यूज तपासणी

        except Exception as e:
            print(f"[Daemon Loop Error]: {e}")
            time.sleep(10)

if __name__ == "__main__":
    start_24x7_daemon()