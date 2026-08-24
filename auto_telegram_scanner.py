import os
import yfinance as yf
import pandas as pd
from quant_engine import analyze_index, build_scanner_row
from telegram_alerts import send_index_signal, send_top_stocks

# Multi-Sector Watchlist Mapping
# Multi-Sector Watchlist Mapping
WATCHLIST_SECTORS = {
    "RELIANCE": "Energy",
    "TCS": "IT",
    "INFY": "IT",
    "HDFCBANK": "Banking",
    "ICICIBANK": "Banking",
    "SBIN": "Banking",
    "BHARTIARTL": "Telecom",
    "TATASTEEL": "Metals",
    "TATAMOTORS": "Auto",
    "M&M": "Auto"
}

def run_15min_cycle():
    print("🚀 [15-Min Execution] Running Institutional Quant Scanner Engine...")
    
    # 1. Analyze Index Options Signals (NIFTY 50 & BANK NIFTY)
    for idx_symbol, idx_name in [("^NSEI", "NIFTY 50"), ("^NSEBANK", "BANK NIFTY")]:
        try:
            df_15m = yf.download(idx_symbol, period="5d", interval="15m", progress=False)
            if isinstance(df_15m.columns, pd.MultiIndex):
                df_15m.columns = df_15m.columns.get_level_values(0)
            
            signal = analyze_index(idx_symbol, df_15m, display_name=idx_name)
            if signal and signal.get("action") != "HOLD / WAIT":
                send_index_signal(signal)
        except Exception as e:
            print(f"[Error] Failed processing index {idx_symbol}: {e}")

    # 2. Equity Breakout Scanner with Volume Surge & Confluence Filtering
    equity_results = []
    for symbol, sector in WATCHLIST_SECTORS.items():
        try:
            yf_ticker = f"{symbol}.NS"
            df_15m = yf.download(yf_ticker, period="5d", interval="15m", progress=False)
            if isinstance(df_15m.columns, pd.MultiIndex):
                df_15m.columns = df_15m.columns.get_level_values(0)
            
            row = build_scanner_row(symbol, df_15m, sector=sector)
            if row and row.get("action") in ["BUY / LONG", "SELL / SHORT"]:
                equity_results.append(row)
        except Exception as e:
            print(f"[Error] Failed scanning stock {symbol}: {e}")

    # Sort results by highest AI confidence score
    equity_results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    
    # Send top 5 high-probability trades to Telegram
    top_signals = equity_results[:5]
    if top_signals:
        send_top_stocks(top_signals)
        print(f"✅ Successfully sent {len(top_signals)} institutional signals to Telegram.")
    else:
        print("ℹ️ Market condition is neutral/choppy. No high-confluence trades triggered.")

if __name__ == "__main__":
    run_15min_cycle()