import os
import time
from data_engine import fetch_stock_data
from quant_engine import analyze_institutional_matrix

WATCHLIST = ["^NSEI", "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"]

def send_telegram_alert(message: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("⚠️ Telegram credentials (BOT_TOKEN / CHAT_ID) सापडले नाहीत.")
        return

    try:
        import requests
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
        print("✅ Telegram alert sent successfully!")
    except Exception as e:
        print(f"❌ Telegram alert failed: {e}")

def run_15min_cycle():
    """GitHub Actions आणि Live Scanner द्वारे कॉल होणारे मुख्य फंक्शन"""
    print("🚀 Starting 15-Minute Quant AI Market Scan...")
    
    for symbol in WATCHLIST:
        try:
            df = fetch_stock_data(symbol, period="5d", interval="15m")
            if df.empty:
                print(f"⚠️ {symbol}: डेटा उपलब्ध नाही")
                continue
            
            res = analyze_institutional_matrix(df)
            action = res.get("action", "HOLD / WAIT")
            confidence = res.get("confidence", 0)
            price = res.get("price", 0.0)
            
            print(f"📊 [{symbol}] Action: {action} | Confidence: {confidence}% | Price: ₹{price}")
            
            if action in ["BUY / LONG", "SELL / SHORT"] and confidence >= 75:
                reasons_text = "\n".join([f"• {r}" for r in res.get("reasons", [])])
                alert_msg = (
                    f"🚨 *QUANT AI SIGNAL ALERT*\n\n"
                    f"📌 *Symbol:* {symbol}\n"
                    f"🎯 *Action:* {action}\n"
                    f"🔥 *Confidence:* {confidence}%\n"
                    f"💰 *Entry Price:* ₹{price}\n\n"
                    f"🎯 *Target 1:* ₹{res.get('tp1')}\n"
                    f"🎯 *Target 2:* ₹{res.get('tp2')}\n"
                    f"🛑 *Stop Loss:* ₹{res.get('sl')}\n\n"
                    f"💡 *Quant Rationale:*\n{reasons_text}"
                )
                send_telegram_alert(alert_msg)
                
        except Exception as e:
            print(f"❌ Error scanning {symbol}: {e}")
            
    print("✅ 15-Minute Scan Cycle Completed.")

if __name__ == "__main__":
    run_15min_cycle()