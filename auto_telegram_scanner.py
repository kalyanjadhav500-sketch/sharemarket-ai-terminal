import time
from config import WATCHLIST
from data_engine import fetch_history, fetch_many
from quant_engine import analyze_index, build_scanner_row
from telegram_alerts import send_index_update, send_top_stocks
from news_engine import fetch_market_news

def run_15min_cycle():
    print("🔄 [15-Min Execution] Fetching Live Data, News & Quant Signals...")

    # 1. Fetch News
    news = fetch_market_news()

    # 2. Analyze Major Indices (NIFTY 50, BANK NIFTY, SENSEX)
    index_targets = [
        ("NIFTY 50", "^NSEI"),
        ("BANK NIFTY", "^NSEBANK"),
        ("SENSEX", "^BSESN")
    ]
    indices_results = []
    for name, sym in index_targets:
        df_idx = fetch_history(sym, "5d", "15m")
        res = analyze_index(sym, df_idx, name)
        if res:
            indices_results.append(res)

    if indices_results:
        send_index_update(indices_results, news)
        print("✅ Index Analysis & News Sent to Telegram.")

    # 3. Fetch Stock Data (15m and Daily for Multi-Timeframe)
    stock_frames_15m = fetch_many(WATCHLIST, "5d", "15m", workers=5)
    stock_frames_daily = fetch_many(WATCHLIST, "3mo", "1d", workers=5)

    rows = []
    for symbol in WATCHLIST:
        df_15m = stock_frames_15m.get(symbol)
        df_daily = stock_frames_daily.get(symbol)
        if df_15m is not None and not df_15m.empty:
            sector = "BANKING" if symbol.startswith(("HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK")) else "EQUITY"
            row = build_scanner_row(symbol, df_15m, df_daily if df_daily is not None else df_15m, sector)
            if row:
                rows.append(row)

    # Confidence नुसार शॉर्टलिस्ट करणे
    rows = sorted(rows, key=lambda x: x["confidence"], reverse=True)
    top_5 = rows[:5]

    if top_5:
        send_top_stocks(top_5)
        print(f"✅ Top Stock Alerts Sent to Telegram: {[s['symbol'] for s in top_5]}")

if __name__ == "__main__":
    print("🚀 AI Agent Execution Loop Started...")
    run_15min_cycle()