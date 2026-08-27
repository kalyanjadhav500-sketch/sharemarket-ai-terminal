import json
import os
from datetime import datetime

PORTFOLIO_FILE = "paper_portfolio.json"

def get_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        default_data = {"capital": 100000.0, "positions": {}, "history": []}
        save_portfolio(default_data)
        return default_data
    with open(PORTFOLIO_FILE, "r") as f:
        return json.load(f)

def save_portfolio(data):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=4)

def execute_paper_trade(symbol: str, action: str, price: float, qty: int = 10, sl: float = 0.0, tp: float = 0.0):
    portfolio = get_portfolio()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # १. नव्याने पोझिशन घेणे (BUY/SELL)
    if symbol not in portfolio["positions"]:
        if action in ["BUY / LONG", "SELL / SHORT"]:
            required_cap = price * qty
            if portfolio["capital"] < required_cap:
                return f"⚠️ अपुरे व्हर्च्युअल भांडवल. आवश्यक: ₹{required_cap:.2f}"
            
            portfolio["capital"] -= required_cap
            portfolio["positions"][symbol] = {
                "action": action,
                "qty": qty,
                "entry_price": price,
                "sl": sl,
                "tp": tp,
                "entry_time": now
            }
            portfolio["history"].append({"time": now, "symbol": symbol, "type": "ENTRY", "action": action, "price": price, "qty": qty})
            save_portfolio(portfolio)
            return f"🟢 [PAPER TRADE] Executed {action} for {symbol} @ ₹{price} (Qty: {qty})"

    # २. अस्तित्वात असलेली पोझिशन बंद करणे (Exit)
    else:
        pos = portfolio["positions"][symbol]
        if (pos["action"] == "BUY / LONG" and action == "SELL / SHORT") or \
           (pos["action"] == "SELL / SHORT" and action == "BUY / LONG") or action == "EXIT":
            
            pnl = (price - pos["entry_price"]) * pos["qty"] if pos["action"] == "BUY / LONG" else (pos["entry_price"] - price) * pos["qty"]
            portfolio["capital"] += (pos["entry_price"] * pos["qty"]) + pnl
            del portfolio["positions"][symbol]
            
            portfolio["history"].append({"time": now, "symbol": symbol, "type": "EXIT", "price": price, "pnl": round(pnl, 2)})
            save_portfolio(portfolio)
            return f"🔴 [PAPER TRADE] Closed Position for {symbol} @ ₹{price} | P&L: ₹{pnl:.2f}"

    return "ℹ️ नो नवीन ट्रेड्स."