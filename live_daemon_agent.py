import time
import datetime
import pytz
import yfinance as yf
import pandas as pd
from quant_engine import analyze_index, build_scanner_row
from news_engine import fetch_global_market_sentiment
from telegram_alerts import send_telegram_message, send_index_signal, send_top_stocks

WATCHLIST_SECTORS = {
    "RELIANCE": "Energy", "TCS": "IT", "INFY": "IT",
    "HDFCBANK": "Banking", "ICICIBANK": "Banking", "SBIN": "Banking",
    "BHARTIARTL": "Telecom", "TATASTEEL": "Metals", "TATAMOTORS": "Auto"
}

ist = pytz.timezone('Asia/Kolkata')

# State Tracker
latest_index_signals = {}
latest_equity_signals = []
last_telegram_dispatch = None
pre_market_sent_date = None  # Tracks if morning pre-market briefing was sent

def is_market_hours():
    now = datetime.datetime.now(ist)
    if now.weekday() >= 5:  # Weekend Check
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

def continuous_market_surveillance():
    """Continuously monitors real-time ticks, price action, and order flow."""
    global latest_index_signals, latest_equity_signals
    
    # 1. Index Surveillance
    for idx_symbol, idx_name in [("^NSEI", "NIFTY 50"), ("^NSEBANK", "BANK NIFTY")]:
        try:
            df = yf.download(idx_symbol, period="1d", interval="1m", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if not df.empty and len(df) > 2:
                signal = analyze_index(idx_symbol, df, display_name=idx_name)
                latest_index_signals[idx_name] = signal
        except Exception as e:
            print(f"[Live Watch Error - {idx_name}]: {e}")

    # 2. Equity Watchlist Scan
    scanned_stocks = []
    for symbol, sector in WATCHLIST_SECTORS.items():
        try:
            df = yf.download(f"{symbol}.NS", period="1d", interval="1m", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if not df.empty and len(df) > 2:
                row = build_scanner_row(symbol, df, sector=sector)
                if row and row.get("action") in ["BUY / LONG", "SELL / SHORT"]:
                    scanned_stocks.append(row)
        except Exception as e:
            print(f"[Live Watch Error - {symbol}]: {e}")

    if scanned_stocks:
        scanned_stocks.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        latest_equity_signals = scanned_stocks

def dispatch_15min_telegram_alerts():
    """Sends high-confluence alerts every 15 minutes during live market hours."""
    global latest_index_signals, latest_equity_signals
    
    now_str = datetime.datetime.now(ist).strftime('%H:%M:%S')
    print(f"📢 [{now_str}] Executing 15-Minute Telegram Call Dispatch...")

    for idx_name, signal in latest_index_signals.items():
        if signal.get("action") in ["BUY CALL (CE)", "BUY PUT (PE)"]:
            send_index_signal(signal)

    if latest_equity_signals:
        top_pick = latest_equity_signals[0]
        send_top_stocks([top_pick])

def send_pre_market_briefing():
    """Sends ONLY ONE Pre-Market Briefing report before market opens (8:45 AM - 9:00 AM)."""
    global pre_market_sent_date
    today_date = datetime.datetime.now(ist).date()
    
    if pre_market_sent_date == today_date:
        return  # Already sent today

    now_str = datetime.datetime.now(ist).strftime('%H:%M:%S')
    print(f"🌅 [{now_str}] Preparing Morning Pre-Market Briefing...")
    
    bias, details = fetch_global_market_sentiment()
    details_formatted = "\n".join([f"• <b>{k}:</b> {v}%" for k, v in details.items()])
    
    msg = (
        f"🌅 <b>PRE-MARKET AI BRIEFING & TODAY'S OUTLOOK</b>\n"
        f"───────────────\n"
        f"🎯 <b>Expected Market Bias Today:</b> {bias}\n"
        f"───────────────\n"
        f"📊 <b>Overnight Global Cues & Forex Study:</b>\n"
        f"{details_formatted}\n\n"
        f"⚡ <i>AI Agent is now active for Live Market surveillance. First 15-min call cycle starts at 09:30 AM.</i>"
    )
    
    if send_telegram_message(msg):
        pre_market_sent_date = today_date
        print("[Pre-Market] Morning Briefing successfully delivered.")

def start_24x7_daemon():
    global last_telegram_dispatch
    print("🤖 [STARTING CONTINUOUS 24/7 QUANT AI DAEMON] 🤖")

    while True:
        try:
            now = datetime.datetime.now(ist)
            
            # 1. LIVE MARKET HOURS (9:15 AM - 3:30 PM)
            if is_market_hours():
                continuous_market_surveillance()
                
                # Dispatch Telegram Alert on 15-Minute Cycles (:00, :15, :30, :45)
                if last_telegram_dispatch != now.minute and now.minute % 15 == 0:
                    dispatch_15min_telegram_alerts()
                    last_telegram_dispatch = now.minute
                
                time.sleep(10)  # Continuous tick scan
                
            # 2. PRE-MARKET HOURS (8:45 AM - 9:14 AM)
            elif is_pre_market_time():
                send_pre_market_briefing()
                time.sleep(60)

            # 3. OFF-MARKET HOURS (Silent Background Analysis, Zero Messages)
            else:
                # Agent quietly scans global cues & prepares for next session
                _ = fetch_global_market_sentiment()
                time.sleep(600)  # Silent background check every 10 mins

        except Exception as e:
            print(f"[Daemon Loop Error]: {e}")
            time.sleep(10)

if __name__ == "__main__":
    start_24x7_daemon()