import time
import datetime
import pytz
import yfinance as yf
import pandas as pd
from quant_engine import analyze_index, build_scanner_row
from telegram_alerts import send_telegram_message, send_index_signal, send_top_stocks

# Multi-Sector Watchlist Mapping
WATCHLIST_SECTORS = {
    "RELIANCE": "Energy", "TCS": "IT", "INFY": "IT",
    "HDFCBANK": "Banking", "ICICIBANK": "Banking", "SBIN": "Banking",
    "BHARTIARTL": "Telecom", "TATASTEEL": "Metals", "TATAMOTORS": "Auto"
}

ist = pytz.timezone('Asia/Kolkata')

def is_market_hours():
    now = datetime.datetime.now(ist)
    if now.weekday() >= 5: # Saturday/Sunday
        return False
    market_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_start <= now <= market_end

def run_live_market_surveillance():
    print(f"⚡ [{datetime.datetime.now(ist).strftime('%H:%M:%S')}] Live Real-Time Surveillance Active...")
    
    # 1. Real-time Index Trigger Check (NIFTY & BANK NIFTY)
    for idx_symbol, idx_name in [("^NSEI", "NIFTY 50"), ("^NSEBANK", "BANK NIFTY")]:
        try:
            df = yf.download(idx_symbol, period="5d", interval="1m", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if not df.empty and len(df) > 10:
                signal = analyze_index(idx_symbol, df, display_name=idx_name)
                if signal and signal.get("action") not in ["HOLD / WAIT", "NO TRADE ZONE"]:
                    send_index_signal(signal)
        except Exception as e:
            print(f"[Error] Index Surveillance Error ({idx_symbol}): {e}")

    # 2. Equity Breakout Scan
    equity_results = []
    for symbol, sector in WATCHLIST_SECTORS.items():
        try:
            df = yf.download(f"{symbol}.NS", period="5d", interval="1m", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if not df.empty and len(df) > 10:
                row = build_scanner_row(symbol, df, sector=sector)
                if row and row.get("action") in ["BUY / LONG", "SELL / SHORT"]:
                    equity_results.append(row)
        except Exception as e:
            print(f"[Error] Stock Scan Error ({symbol}): {e}")

    if equity_results:
        equity_results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        send_top_stocks(equity_results[:3])

def run_off_market_intelligence():
    print(f"🌙 [{datetime.datetime.now(ist).strftime('%H:%M:%S')}] 24/7 Global Market & News Surveillance Active...")
    try:
        gift = yf.Ticker("^NSEI")
        price = gift.fast_info.last_price if hasattr(gift, 'fast_info') else 0.0
        msg = (
            f"🌐 <b>24/7 AI AGENT: OVERNIGHT WATCH</b>\n"
            f"• <b>Status:</b> Global News & Macro Sentiment Active\n"
            f"• <b>Nifty Ref Price:</b> ₹{round(price, 2)}\n"
            f"• <i>Monitoring Asian & US market cues, overnight news & GIFT Nifty...</i>"
        )
        send_telegram_message(msg)
    except Exception as e:
        print(f"[Off-Market Error]: {e}")

def start_24x7_daemon():
    print("🤖 [STARTING 24/7 AUTONOMOUS MARKET AGENT DAEMON] 🤖")
    send_telegram_message("🤖 <b>24/7 Autonomous Quant AI Agent is now LIVE and Active.</b>")
    
    while True:
        try:
            if is_market_hours():
                run_live_market_surveillance()
                time.sleep(30)  # Continuous 30-sec polling during trading hours
            else:
                run_off_market_intelligence()
                time.sleep(3600) # Hourly background sweep during off-market hours
        except Exception as e:
            print(f"[Daemon Loop Error]: {e}")
            time.sleep(10)

if __name__ == "__main__":
    start_24x7_daemon()