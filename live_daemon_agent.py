import os
from dotenv import load_dotenv
load_dotenv()

from data_engine import fetch_stock_data
from quant_engine import analyze_institutional_matrix
from broker_engine import execute_paper_trade

# फक्त Nifty 50, Bank Nifty आणि Sensex
INDEX_WATCHLIST = {
    "^NSEI": "NIFTY 50",
    "^NSEBANK": "BANK NIFTY",
    "^BSESN": "SENSEX"
}

def send_telegram_alert(message: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("⚠️ Telegram credentials सापडले नाहीत.")
        return

    try:
        import requests
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
        print("✅ Telegram alert sent!")
    except Exception as e:
        print(f"❌ Telegram alert error: {e}")

def run_15min_cycle():
    print("🚀 Starting Options Quant AI Scan (NIFTY / BANKNIFTY / SENSEX)...")
    
    for symbol, name in INDEX_WATCHLIST.items():
        try:
            df = fetch_stock_data(symbol, period="5d", interval="15m")
            if df.empty:
                print(f"⚠️ {name} ({symbol}): डेटा उपलब्ध नाही")
                continue
            
            res = analyze_institutional_matrix(df)
            action = res.get("action", "HOLD / WAIT")
            confidence = res.get("confidence", 0)
            price = res.get("price", 0.0)
            
            print(f"📊 [{name}] Action: {action} | Confidence: {confidence}% | Spot Price: ₹{price}")
            
            if confidence >= 75 and action in ["BUY / LONG", "SELL / SHORT"]:
                # Option Type ठरवणे (Bullish = CE Buy, Bearish = PE Buy)
                option_type = "BUY CE (CALL)" if action == "BUY / LONG" else "BUY PE (PUT)"
                trade_symbol = f"{name} {option_type}"
                
                # १. पेपर ट्रेडिंग ऑर्डर एक्झिक्युट करणे (१ लॉट व्हर्च्युअल ट्रेड)
                trade_log = execute_paper_trade(
                    symbol=trade_symbol, 
                    action=option_type, 
                    price=price, 
                    qty=1, 
                    sl=res.get('sl'), 
                    tp=res.get('tp1')
                )
                print(f"💼 {trade_log}")

                # २. टेलिग्राम अलर्ट पाठवणे
                reasons_text = "\n".join([f"• {r}" for r in res.get("reasons", [])])
                alert_msg = (
                    f"🚨 *OPTIONS QUANT SIGNAL ALERT*\n\n"
                    f"📌 *Index:* {name}\n"
                    f"⚡ *Option Action:* `{option_type}`\n"
                    f"🔥 *Confidence:* {confidence}%\n"
                    f"💰 *Spot Price:* ₹{price}\n\n"
                    f"🎯 *Target:* ₹{res.get('tp1')}\n"
                    f"🛑 *Stop Loss:* ₹{res.get('sl')}\n\n"
                    f"💡 *Rationale:*\n{reasons_text}"
                )
                send_telegram_alert(alert_msg)
                
        except Exception as e:
            print(f"❌ Error scanning {name}: {e}")
            
    print("✅ Options Scan Cycle Completed.")

if __name__ == "__main__":
    run_15min_cycle()