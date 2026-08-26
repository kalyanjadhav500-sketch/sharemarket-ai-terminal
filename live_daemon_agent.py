import os
import time
import datetime
import requests
from dotenv import load_dotenv
from data_engine import fetch_stock_data
from quant_engine import analyze_institutional_matrix

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[ALERT WARNING] Telegram Bot Token or Chat ID missing in .env")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

def run_market_surveillance():
    watchlist = ["^NSEI", "^NSEBANK", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS"]
    last_alert_time = {}

    print("🤖 Quant AI 24x7 Surveillance Agent Operational...")
    while True:
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M")
        is_market_hours = "09:15" <= current_time <= "15:30" and now.weekday() < 5

        # Pre-Market Outlook Briefing (08:45 - 09:14 IST)
        if "08:45" <= current_time <= "09:14" and now.weekday() < 5:
            if "pre_market_sent" not in last_alert_time or last_alert_time["pre_market_sent"] != now.date():
                brief = "🌅 *PRE-MARKET QUANT OUTLOOK*\n\nMarket surveillance cycle initialized. Models targeting high confluence setups for today's session."
                send_telegram_alert(brief)
                last_alert_time["pre_market_sent"] = now.date()

        if is_market_hours:
            for symbol in watchlist:
                df = fetch_stock_data(symbol, period="5d", interval="5m")
                if df is not None:
                    res = analyze_institutional_matrix(df)
                    if res["confidence"] >= 85:
                        last_sent = last_alert_time.get(symbol, 0)
                        if time.time() - last_sent > 300:  # 5 Minutes Cooldown
                            msg = f"🚨 *HIGH CONFLUENCE TRADE ALERT*\n\n" \
                                  f"📌 *Symbol*: `{symbol}`\n" \
                                  f"⚡ *Action*: *{res['action']}*\n" \
                                  f"💵 *Entry*: ₹{res['entry_price']}\n" \
                                  f"🎯 *Target 1*: ₹{res['target1']}\n" \
                                  f"🎯 *Target 2*: ₹{res['target2']}\n" \
                                  f"🛡️ *Stop Loss*: ₹{res['stop_loss']}\n" \
                                  f"📊 *Score*: {res['confidence']}%\n" \
                                  f"⚖️ *Risk/Reward*: {res['rr_ratio']}"
                            send_telegram_alert(msg)
                            last_alert_time[symbol] = time.time()
        time.sleep(60)

if __name__ == "__main__":
    run_market_surveillance()