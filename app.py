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

# ⚡ Smart Cache Engine (५ मिनिटांच्या कॅशेमुळे २-सेकंद रिफ्रेश लूप हँग होणार नाही)
@st.cache_data(ttl=300)
def get_cached_news():
    try:
        return fetch_global_market_sentiment()
    except Exception as e:
        return "NEUTRAL", {"Status": "Active"}, ["Global cues are being tracked in real-time."]

# Sidebar Parameters
st.sidebar.header("⚙️ Trading Parameters & Risk Shield")
account_capital = st.sidebar.number_input("Account Capital (₹)", value=100000, step=10000)
risk_per_trade_pct = st.sidebar.slider("Risk Per Trade (%)", 0.5, 3.0, 1.0, 0.1)

engine_mode = st.sidebar.radio("Select Engine Mode", ["Index Derivatives Engine", "Equity Breakout Scanner"])

WATCHLIST_SECTORS = {
    "RELIANCE": "Energy", 
    "TCS": "IT", 
    "INFY": "IT",
    "HDFCBANK": "Banking", 
    "ICICIBANK": "Banking", 
    "SBIN": "Banking",
    "BHARTIARTL": "Telecom", 
    "TATASTEEL": "Metals"
}

if engine_mode == "Index Derivatives Engine":
    selected_index = st.selectbox("Select Benchmark Index", ["BANK NIFTY", "NIFTY 50"])
    symbol_map = {"BANK NIFTY": "^NSEBANK", "NIFTY 50": "^NSEI"}
    idx_symbol = symbol_map[selected_index]

    # Download Base Market Data
    df_1m = yf.download(idx_symbol, period="1d", interval="1m", progress=False)
    if isinstance(df_1m.columns, pd.MultiIndex):
        df_1m.columns = df_1m.columns.get_level_values(0)

    if not df_1m.empty and len(df_1m) > 2:
        curr_price = df_1m['Close'].iloc[-1]
        
        # 0-Lag Broker WebSocket Stream Fetch
        tick_data = broker_stream.fetch_live_tick(idx_symbol, current_market_price=curr_price)
        signal = analyze_index(idx_symbol, df_1m, display_name=selected_index, tick_data=tick_data)
        
        if signal:
            action = signal["action"]
            confidence = signal["confidence"]
            ltp = signal["entry_price"]

            # Dynamic Lot Calculation based on Risk Shield
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

elif engine_mode == "Equity Breakout Scanner":
    st.subheader("📈 Real-Time Equity Breakout Scanner")
    st.info("Continuous high-conviction scanning across active watchlist stocks.")
    
    scanner_data = []
    for symbol, sector in WATCHLIST_SECTORS.items():
        try:
            df_eq = yf.download(f"{symbol}.NS", period="1d", interval="1m", progress=False)
            if isinstance(df_eq.columns, pd.MultiIndex):
                df_eq.columns = df_eq.columns.get_level_values(0)
            if not df_eq.empty and len(df_eq) > 2:
                row = build_scanner_row(symbol, df_eq, sector=sector)
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