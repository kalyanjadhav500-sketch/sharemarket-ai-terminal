import os
import requests
import html
import urllib3
from config import SETTINGS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def send_telegram_message(text):
    """टेलिग्रामवर मेसेज पाठवणे"""
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
            verify=False
        )
        return r.ok
    except Exception as e:
        print(f"❌ Telegram Send Exception: {e}")
        return False

def send_telegram_signal(signal_data):
    """app.py आणि Streamlit साठी सिग्नल अलर्ट फंक्शन"""
    if isinstance(signal_data, str):
        return send_telegram_message(signal_data)
    
    emoji = "🟢" if signal_data.get('action') == "BUY" else "🔴"
    text = f"""<b>{emoji} AI TRADING SIGNAL</b>
<b>Symbol:</b> {signal_data.get('symbol')}
<b>Action:</b> {signal_data.get('action')}
<b>Entry:</b> ₹{signal_data.get('price')}
<b>SL:</b> ₹{signal_data.get('sl')}
<b>Target 1:</b> ₹{signal_data.get('tp1')} | <b>Target 2:</b> ₹{signal_data.get('tp2')}
"""
    return send_telegram_message(text)

def send_index_update(indices_data, news_list):
    """इंडेक्स रिपोर्ट पाठवणे"""
    news_text = "\n".join([f"• <i>{html.escape(n)}</i>" for n in news_list])
    text = f"<b>📊 15-MIN INDEX DEEP ANALYSIS</b>\n\n"
    for idx in indices_data:
        emoji = "🟢" if idx['action'].startswith("BUY") else ("🔴" if idx['action'].startswith("SELL") else "🟡")
        text += f"""<b>{emoji} {idx['name']} ({idx['price']})</b>
• <b>Action:</b> {idx['action']}
• <b>Entry:</b> ₹{idx['entry']} | <b>SL:</b> ₹{idx['sl']} | <b>Target:</b> ₹{idx['tp']}
• <b>RSI:</b> {idx['rsi']} | <b>Bias:</b> {idx['bias']}
------------------------------\n"""
    text += f"<b>📰 Live News & Sentiment (24/7):</b>\n{news_text}"
    send_telegram_message(text)

def send_top_stocks(stocks):
    """टॉप स्टॉक कॉल्स पाठवणे"""
    text = "<b>🚨 AI AGENT: TOP HIGH-CONVICTION CALLS</b>\n"
    text += "<i>24/7 Deep Research & Multi-Timeframe Study Engine</i>\n\n"
    
    for i, s in enumerate(stocks[:5], 1):
        emoji = "🟢" if s['action'] == "BUY" else "🔴"
        reasons_text = "\n".join([f"  • {r}" for r in s['reasons']])
        
        text += f"""<b>#{i} {emoji} {html.escape(s['symbol'])}</b> ({s['sector']})
• <b>Action:</b> {s['action']} | <b>AI Confidence:</b> {s['confidence']}%
• <b>Entry Level:</b> ₹{s['price']}
• <b>Stop Loss (SL):</b> ₹{s['sl']}
• <b>Target 1:</b> ₹{s['tp1']} | <b>Target 2:</b> ₹{s['tp2']}
<b>💡 AI Deep Study Reasoning (हा कॉल का दिला?):</b>
{reasons_text}
----------------------------------------\n"""
        
    text += "\n<i>⚠️ Intraday Trading Note: 3:15 PM च्या आधी पोझिशन स्क्वेअर-ऑफ करा.</i>"
    send_telegram_message(text)