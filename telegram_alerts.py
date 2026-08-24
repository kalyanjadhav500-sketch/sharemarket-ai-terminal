import os
import requests
import html

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message_text):
    """Sends a raw formatted HTML message to the configured Telegram chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram Alerts] Missing API credentials in Environment Variables.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=12)
        if response.status_code == 200:
            print("[Telegram Alerts] Message successfully sent.")
            return True
        else:
            print(f"[Telegram Alerts] Failed to send. Server response: {response.text}")
            return False
    except Exception as e:
        print(f"[Telegram Alerts] Exception during delivery: {e}")
        return False

def send_index_signal(signal_data):
    """Formats and sends institutional index trading signals (NIFTY/BANKNIFTY)."""
    if not signal_data:
        return
    
    action = signal_data.get('action', 'NO TRADE')
    emoji = "🚀" if "BUY" in action else ("💥" if "SELL" in action else "⏸️")
    
    pivots_str = ""
    if signal_data.get('pivots'):
        p = signal_data['pivots']
        pivots_str = f"📍 <b>Pivots:</b> P: {p['pivot']} | R1: {p['r1']} | S1: {p['s1']}\n"

    msg = (
        f"🏛️ <b>INSTITUTIONAL INDEX ANALYSIS</b> 🏛️\n"
        f"<b>Asset:</b> {html.escape(signal_data.get('name', 'INDEX'))}\n"
        f"<b>Signal:</b> {emoji} <b>{action}</b>\n"
        f"<b>Current Price:</b> ₹{signal_data.get('price', 0.0)}\n"
        f"<b>AI Confidence:</b> {signal_data.get('confidence', 0)}%\n"
        f"{pivots_str}"
        f"<b>Recommended Position Size:</b> {signal_data.get('position_size', 1)} Lot(s)\n"
        f"───────────────\n"
        f"🎯 <b>Target 1:</b> ₹{signal_data.get('tp1', 0.0)}\n"
        f"🎯 <b>Target 2:</b> ₹{signal_data.get('tp2', 0.0)}\n"
        f"🛑 <b>Stop Loss:</b> ₹{signal_data.get('sl', 0.0)}\n"
        f"───────────────\n"
        f"💡 <b>Quant Rationale:</b>\n"
    )
    
    for r in signal_data.get('reasons', []):
        msg += f"• {r}\n"

    send_telegram_message(msg)

def send_top_stocks(top_stocks_list):
    """Formats and sends top intraday/swing equity breakout signals."""
    if not top_stocks_list:
        return

    msg = "⚡ <b>QUANT AGENT: TOP EQUITY BREAKOUTS</b> ⚡\n\n"
    
    for idx, s in enumerate(top_stocks_list, 1):
        action = s.get('action', 'NO TRADE')
        emoji = "🟢" if "BUY" in action else ("🔴" if "SELL" in action else "⚪")
        pivots_str = ""
        if s.get('pivots'):
            p = s['pivots']
            pivots_str = f"   ├ Pivots: P: {p['pivot']} | R1: {p['r1']}\n"
        
        msg += (
            f"<b>#{idx} {s.get('symbol')}</b> ({s.get('sector', 'Equity')})\n"
            f"   ├ Action: {emoji} <b>{action}</b> @ ₹{s.get('price')}\n"
            f"   ├ Rec. Qty (1% Risk): <b>{s.get('position_size', 1)} shares</b>\n"
            f"   ├ Targets: ₹{s.get('tp1')} / ₹{s.get('tp2')}\n"
            f"   ├ Stop Loss: ₹{s.get('sl')}\n"
            f"{pivots_str}"
            f"   └ Confidence: {s.get('confidence')}%\n\n"
        )
    
    send_telegram_message(msg)