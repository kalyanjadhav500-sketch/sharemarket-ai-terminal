import os
import requests
import html
import urllib3
from config import SETTINGS

# SSL वॉर्निंग बंद करण्यासाठी
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def send_telegram_message(text):
    token = SETTINGS.telegram_token
    chat = SETTINGS.telegram_chat_id
    if not token or not chat:
        print("❌ [Telegram Error] Token किंवा Chat ID सेट नाही.")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "parse_mode": "HTML"},
            timeout=12,
            verify=False  # SSL एरर फिक्स
        )
        return r.ok
    except Exception as e:
        print(f"❌ Telegram Send Exception: {e}")
        return False

def send_index_update(indices_data, news_list):
    news_text = "\n".join([f"• <i>{html.escape(n)}</i>" for n in news_list])
    text = f"""<b>📊 15-MIN INDEX DEEP ANALYSIS</b>\n\n"""
    for idx in indices_data:
        emoji = "🟢" if idx['action'].startswith("BUY") else ("🔴" if idx['action'].startswith("SELL") else "🟡")
        text += f"""<b>{emoji} {idx['name']} ({idx['price']})</b>
• <b>Action:</b> {idx['action']}
• <b>Entry:</b> ₹{idx['entry']} | <b>SL:</b> ₹{idx['sl']} | <b>Target:</b> ₹{idx['tp']}
• <b>RSI:</b> {idx['rsi']} | <b>Bias:</b> {idx['bias']}
------------------------------
"""
    text += f"""<b>📰 Live News & Sentiment (24/7):</b>\n{news_text}"""
    send_telegram_message(text)

def send_top_stocks(stocks):
    text = "<b>🚨 TOP 5 QUANT STOCKS (15-MIN CALLS)</b>\n\n"
    for i, s in enumerate(stocks[:5], 1):
        emoji = "🟢" if s['action'] == "BUY" else ("🔴" if s['action'] == "SELL" else "🟡")
        text += f"""<b>#{i} {emoji} {html.escape(s['symbol'])}</b> ({s['sector']})
• <b>Action:</b> {s['action']} (Conviction: {s['confidence']}/100)
• <b>Entry Range:</b> ₹{s['entry_low']} – ₹{s['entry_high']}
• <b>Stop Loss (SL):</b> ₹{s['sl']}
• <b>Target 1 (TP1):</b> ₹{s['tp1']} | <b>TP2:</b> ₹{s['tp2']}
• <b>R:R:</b> 1:{s['rr']} | <b>Smart Money:</b> {s['smart_money']}/100\n\n"""
    text += "<i>AI Agent Automated 15-Min Execution. Always manage your risk!</i>"
    send_telegram_message(text)