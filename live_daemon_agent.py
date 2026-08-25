import time
import datetime
import pytz
import yfinance as yf
import pandas as pd
from quant_engine import analyze_index, build_scanner_row
from news_engine import fetch_global_market_sentiment
from telegram_alerts import send_telegram_message, send_index_signal, send_top_stocks
from broker_engine import broker_stream

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
    """Direct Broker WebSocket Tick Surveillance with Zero-Lag Logic."""
    global latest_index_signals, latest_equity_signals, last_alert_sent
    
    for idx_symbol, idx_name in [("^NSEI", "NIFTY 50"), ("^NSEBANK", "BANK NIFTY")]:
        try:
            df_1m = yf.download(idx_symbol, period="1d", interval="1m", progress=False)
            if isinstance(df_1m.columns, pd.MultiIndex):
                df_1m.columns = df_1m.columns.get_level_values(0)
            
            if not df_1m.empty and len(df_1m) > 2:
                # 0-Lag Tick Data Fetching from Broker Bridge Engine
                curr_price = df_1m['Close'].iloc[-1]
                tick_data = broker_stream.fetch_live_tick(idx_symbol, current_market_price=curr_price)
                
                # Dynamic Quant Execution with Tick Imbalance
                signal = analyze_index(idx_symbol, df_1m, display_name=idx_name, tick_data=tick_data)
                
                if signal:
                    signal['news_bias'] = current_news_sentiment['bias']
                    signal['news_headlines'] = current_news_sentiment.get('headlines', [])
                    latest_index_signals[idx_name] = signal
                    
                    action = signal.get("action")
                    if action in ["BUY CALL (CE)", "BUY PUT (PE)"]:
                        last_time = last_alert_sent.get(idx_name)
                        now_time = time.time()
                        
                        if not last_time or (now_time - last_time > 300):
                            send_index_signal(signal)
                            last_alert_sent[idx_name] = now_time
                            print(f"⚡ [0-LAG HFT ALERT SENT]: {idx_name} -> {action}")
        except Exception as e:
            print(f"[Real-Time Watch Error - {idx_name}]: {e}")

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
        f"🌅 <b>24x7 AI AGENT: PRE-MARKET OUTLOOK</b>\n"
        f"───────────────\n"
        f"🎯 <b>Live Sentiment Bias:</b> {bias}\n"
        f"───────────────\n"
        f"📊 <b>Global Cues & Quant Drivers:</b>\n"
        f"{details_formatted}\n\n"
        f"🔥 <b>Top Real-Time Headlines:</b>\n"
        f"{headlines_formatted}\n\n"
        f"⚡ <i>Broker WebSocket Tick Stream Active.</i>"
    )
    
    if send_telegram_message(msg):
        pre_market_sent_date = today_date
        print("[Pre-Market] Morning Briefing successfully delivered.")

def start_24x7_daemon():
    print("🤖 [STARTING BROKER TICK-STREAM ZERO-LAG AI DAEMON] 🤖")
    broker_stream.connect()
    
    news_timer = 0
    while True:
        try:
            if time.time() - news_timer > 900:
                update_live_news_sentiment()
                news_timer = time.time()

            if is_market_hours():
                continuous_realtime_surveillance()
                time.sleep(2)  # २ सेकंदांच्या 0-Lag स्पीड लूपवर स्कॅनिंग
                
            elif is_pre_market_time():
                send_pre_market_briefing()
                time.sleep(60)

            else:
                time.sleep(300)

        except Exception as e:
            print(f"[Daemon Loop Error]: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_24x7_daemon()