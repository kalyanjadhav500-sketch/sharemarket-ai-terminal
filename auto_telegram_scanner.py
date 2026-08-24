import time
from config import WATCHLIST, INDICES, SECTOR_INDICES
from data_engine import fetch_history, fetch_many
from quant_engine import market_regime, sector_strength, build_scanner_row, analyze_index
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

    # 3. Analyze Top 5 Stocks
    nifty_df = fetch_history(INDICES["NIFTY 50"], "6mo", "1d")
    regime = market_regime(nifty_df)
    sector_frames = fetch_many(list(SECTOR_INDICES.values()), "3mo", "1d", workers=5)
    sector_map = {name: sector_frames.get(sym) for name, sym in SECTOR_INDICES.items()}
    sectors = sector_strength(sector_map)
    sector_scores = dict(zip(sectors["sector"], sectors["rank_score"])) if not sectors.empty else {}

    stock_frames = fetch_many(WATCHLIST, "5d", "15m", workers=8)
    rows = []
    for symbol, df in stock_frames.items():
        sector = "BANKING" if symbol.startswith(("HDFCBANK", "ICICIBANK", "SBIN")) else "N/A"
        score = sector_scores.get(sector, 50)
        row = build_scanner_row(symbol, df, regime, score, sector)
        if row:
           
            if row["action"] == "NO TRADE":
                row["action"] = "BUY" if row["bull_score"] >= row["bear_score"] else "SELL"
            rows.append(row)

   
    rows = sorted(rows, key=lambda x: x["confidence"], reverse=True)
    top_5 = rows[:5]

    if top_5:
        send_top_stocks(top_5)
        print(f"✅ Top 5 Stock Alerts Sent to Telegram: {[s['symbol'] for s in top_5]}")

if __name__ == "__main__":
    print("🚀 AI Agent 15-Min Telegram Automation Engine Started!")
    while True:
        try:
            run_15min_cycle()
        except Exception as e:
            print("❌ Loop Error:", e)
        
        print("⏰ Sleeping for 15 minutes (900 seconds)...")
        time.sleep(900)  