import streamlit as st
import pandas as pd
import yfinance as yf
import time
from quant_engine import analyze_index, build_scanner_row
from broker_engine import broker_stream
from news_engine import fetch_global_market_sentiment

# Page Configuration
st.set_page_config(page_title="Quant AI Trading Terminal", layout="wide")

st.title("⚡ Quant AI Trading Terminal (0-Lag HFT Engine)")

# 📰 Smart Cache News Engine (५ मिनिटांचा स्मार्ट कॅशे)
@st.cache_data(ttl=300)
def get_cached_news():
    try:
        bias, details, headlines = fetch_global_market_sentiment()
        return bias, details, headlines
    except Exception as e:
        return "NEUTRAL", {"Global Bias": "Neutral / Tracking"}, [
            "RBI & Fed Monetary Policy Updates Monitored.",
            "Global Cues trading with neutral bias.",
            "Institutional Volume Stream Active."
        ]

# Sidebar Parameters
st.sidebar.header("⚙️ Trading Parameters & Risk Shield")
account_capital = st.sidebar.number_input("Account Capital (₹)", value=100000, step=10000)
risk_per_trade_pct = st.sidebar.slider("Risk Per Trade (%)", 0.5, 3.0, 1.0, 0.1)

engine_mode = st.sidebar.radio("Select Engine Mode", ["Index Derivatives Engine", "Equity Breakout Scanner & Search"])

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
    "LT": "Infrastructure"
}

if engine_mode == "Index Derivatives Engine":
    selected_index = st.selectbox("Select Benchmark Index", ["BANK NIFTY", "NIFTY 50"])
    symbol_map = {"BANK NIFTY": "^NSEBANK", "NIFTY 50": "^NSEI"}
    idx_symbol = symbol_map[selected_index]

    df_1m = yf.download(idx_symbol, period="1d", interval="1m", progress=False)
    if isinstance(df_1m.columns, pd.MultiIndex):
        df_1m.columns = df_1m.columns.get_level_values(0)

    if not df_1m.empty and len(df_1m) > 2:
        curr_price = df_1m['Close'].iloc[-1]
        tick_data = broker_stream.fetch_live_tick(idx_symbol, current_market_price=curr_price)
        signal = analyze_index(idx_symbol, df_1m, display_name=selected_index, tick_data=tick_data)
        
        if signal:
            action = signal["action"]
            confidence = signal["confidence"]
            ltp = signal["entry_price"]

            lot_size_map = {"BANK NIFTY": 15, "NIFTY 50": 25}
            risk_amount = (account_capital * risk_per_trade_pct) / 100
            recommended_lots = max(1, int(risk_amount / (lot_size_map[selected_index] * 50)))

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Current Price", f"₹{ltp}")
            col2.metric("Execution Action", action)
            col3.metric("AI Confidence Score", f"{confidence}%")
            col4.metric("Recommended Size", f"{recommended_lots} Lot(s)")

            st.markdown("---")
            st.subheader("🎯 Institutional Trade Levels & Risk Parameters")

            col_left, col_right = st.columns(2)
            with col_left:
                st.write("**Targets & Stop Loss**")
                st.json({
                    "Entry Price": ltp if action != "HOLD / WAIT" else "N/A",
                    "Target 1": signal["target1"],
                    "Target 2": signal["target2"],
                    "Stop Loss": signal["stop_loss"],
                    "Risk / Reward Ratio": signal["rr_ratio"]
                })
            with col_right:
                st.write("**Daily Pivot Levels**")
                st.json(signal["pivots"])

            st.markdown("---")
            st.subheader("💡 Quant Logic & Confluence Factors")
            for reason in signal["reasons"]:
                st.write(f"• {reason}")

elif engine_mode == "Equity Breakout Scanner & Search":
    st.subheader("🔍 Equity Stock Search & Real-Time Quant Analysis")
    
    # Live Search Input & Dropdown
    search_col1, search_col2 = st.columns([2, 1])
    with search_col1:
        custom_input = st.text_input("🔍 Type Stock Symbol (e.g. TATAMOTORS, RELIANCE, SBIN, INFY):", value="RELIANCE").upper().strip()
    with search_col2:
        quick_select = st.selectbox("Or Quick Select Watchlist:", ["CUSTOM SEARCH"] + list(WATCHLIST_SECTORS.keys()))
        
    stock_symbol = custom_input if quick_select == "CUSTOM SEARCH" else quick_select
    stock_ticker = f"{stock_symbol}.NS" if not stock_symbol.endswith(".NS") else stock_symbol
    
    st.markdown(f"### 🎯 Quant Analysis for **{stock_symbol}**")
    
    df_eq = yf.download(stock_ticker, period="1d", interval="1m", progress=False)
    if isinstance(df_eq.columns, pd.MultiIndex):
        df_eq.columns = df_eq.columns.get_level_values(0)
        
    if not df_eq.empty and len(df_eq) > 2:
        eq_price = df_eq['Close'].iloc[-1]
        tick_data = broker_stream.fetch_live_tick(stock_ticker, current_market_price=eq_price)
        signal = analyze_index(stock_ticker, df_eq, display_name=stock_symbol, tick_data=tick_data)
        
        if signal:
            action = signal["action"]
            confidence = signal["confidence"]
            ltp = signal["entry_price"]

            risk_amount = (account_capital * risk_per_trade_pct) / 100
            sl_val = signal["stop_loss"]
            sl_dist = abs(ltp - sl_val) if isinstance(sl_val, (int, float)) else ltp * 0.01
            rec_shares = max(1, int(risk_amount / (sl_dist if sl_dist > 0 else 1)))

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Current Price", f"₹{ltp}")
            col2.metric("Execution Action", action)
            col3.metric("AI Confidence Score", f"{confidence}%")
            col4.metric("Recommended Size", f"{rec_shares} Share(s)")

            st.markdown("---")
            st.subheader("🎯 Institutional Trade Levels & Risk Parameters")

            col_left, col_right = st.columns(2)
            with col_left:
                st.write("**Targets & Stop Loss**")
                st.json({
                    "Entry Price": ltp if action != "HOLD / WAIT" else "N/A",
                    "Target 1": signal["target1"],
                    "Target 2": signal["target2"],
                    "Stop Loss": signal["stop_loss"],
                    "Risk / Reward Ratio": signal["rr_ratio"]
                })
            with col_right:
                st.write("**Daily Pivot Levels**")
                st.json(signal["pivots"])

            st.markdown("---")
            st.subheader("💡 Quant Logic & Confluence Factors")
            for reason in signal["reasons"]:
                st.write(f"• {reason}")
    else:
        st.error(f"⚠️ '{stock_symbol}' साठी डेटा उपलब्ध नाही. कृपया अचूक NSE सिम्बॉल टाका (उदा. TATAMOTORS, INFY).")

    st.markdown("---")
    st.subheader("📈 Watchlist Breakout Scanner")
    scanner_data = []
    for symbol, sector in WATCHLIST_SECTORS.items():
        try:
            df_sec = yf.download(f"{symbol}.NS", period="1d", interval="1m", progress=False)
            if isinstance(df_sec.columns, pd.MultiIndex):
                df_sec.columns = df_sec.columns.get_level_values(0)
            if not df_sec.empty and len(df_sec) > 2:
                row = build_scanner_row(symbol, df_sec, sector=sector)
                if row:
                    scanner_data.append(row)
        except Exception:
            pass

    if scanner_data:
        st.dataframe(pd.DataFrame(scanner_data), use_container_width=True)

# 📰 LIVE MARKET NEWS & GLOBAL SENTIMENT SECTION
st.markdown("---")
st.subheader("📰 Live Market News & Global Sentiment")

bias, details, headlines = get_cached_news()
col_n1, col_n2 = st.columns([1, 2])

with col_n1:
    st.metric("Overall Market Bias", bias)
    st.write("**Global Drivers & Macro Metrics**")
    st.json(details)
    
with col_n2:
    st.write("**Top Live Headlines**")
    if headlines:
        for h in headlines:
            st.write(f"• {h}")
    else:
        st.write("• Global markets trading in neutral territory.")

# Continuous Live Refresh Loop
time.sleep(2)
st.rerun()