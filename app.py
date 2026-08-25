import streamlit as st
import pandas as pd
import yfinance as yf
import time
from quant_engine import analyze_index
from broker_engine import broker_stream
from news_engine import fetch_global_market_sentiment

st.set_page_config(page_title="Quant AI Trading Terminal", layout="wide")
st.title("⚡ Quant AI Trading Terminal (Institutional Engine)")

@st.cache_data(ttl=180)
def get_cached_news(symbol_name):
    return fetch_global_market_sentiment(symbol=symbol_name)

st.sidebar.header("⚙️ Trading Parameters & Risk Shield")
account_capital = st.sidebar.number_input("Account Capital (₹)", value=100000, step=10000)
risk_per_trade_pct = st.sidebar.slider("Risk Per Trade (%)", 0.5, 3.0, 1.0, 0.1)

engine_mode = st.sidebar.radio("Select Engine Mode", ["Index Derivatives Engine", "Equity Stock Search Engine"])

active_symbol_for_news = "BANK NIFTY"

if engine_mode == "Index Derivatives Engine":
    selected_index = st.selectbox("Select Benchmark Index", ["BANK NIFTY", "NIFTY 50"])
    symbol_map = {"BANK NIFTY": "^NSEBANK", "NIFTY 50": "^NSEI"}
    idx_symbol = symbol_map[selected_index]
    active_symbol_for_news = selected_index

    # 🛡️ FIX: Fetching 5-minute Candles instead of 1-minute to eliminate tick noise
    df_5m = yf.download(idx_symbol, period="5d", interval="5m", progress=False)
    if isinstance(df_5m.columns, pd.MultiIndex):
        df_5m.columns = df_5m.columns.get_level_values(0)

    if not df_5m.empty and len(df_5m) > 15:
        curr_price = df_5m['Close'].iloc[-1]
        tick_data = broker_stream.fetch_live_tick(idx_symbol, current_market_price=curr_price)
        signal = analyze_index(idx_symbol, df_5m, display_name=selected_index, tick_data=tick_data)
        
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
                    "Entry Price": ltp if "BUY" in action else "N/A",
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

elif engine_mode == "Equity Stock Search Engine":
    st.subheader("🔍 Dynamic Equity Stock Search")
    user_stock = st.text_input("🔍 Type Stock Symbol (e.g. RELIANCE, TATAMOTORS, SBIN):", value="RELIANCE").upper().strip()
    
    if user_stock:
        stock_ticker = f"{user_stock}.NS" if not user_stock.endswith(".NS") else user_stock
        clean_name = user_stock.replace(".NS", "")
        active_symbol_for_news = clean_name
        
        st.markdown(f"### 🎯 Real-Time Quant Analysis for **{clean_name}**")
        
        try:
            # 🛡️ FIX: 5-minute Candles for Equity to stabilize signals
            df_eq = yf.download(stock_ticker, period="5d", interval="5m", progress=False)
            if isinstance(df_eq.columns, pd.MultiIndex):
                df_eq.columns = df_eq.columns.get_level_values(0)
                
            if not df_eq.empty and len(df_eq) > 15:
                eq_price = df_eq['Close'].iloc[-1]
                tick_data = broker_stream.fetch_live_tick(stock_ticker, current_market_price=eq_price)
                signal = analyze_index(stock_ticker, df_eq, display_name=clean_name, tick_data=tick_data)
                
                if signal:
                    action = signal["action"]
                    confidence = signal["confidence"]
                    ltp = signal["entry_price"]

                    risk_amount = (account_capital * risk_per_trade_pct) / 100
                    sl_val = signal["stop_loss"]
                    sl_dist = abs(ltp - sl_val) if isinstance(sl_val, (int, float)) and sl_val != 0 else (ltp * 0.008)
                    rec_shares = max(1, int(risk_amount / sl_dist))

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
                            "Entry Price": ltp if "BUY" in action else "N/A",
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
                st.error(f"⚠️ '{clean_name}' साठी पुरेसा डेटा उपलब्ध नाही.")
        except Exception as e:
            st.error(f"⚠️ डेटा फेच करताना एरर आला: {e}")

st.markdown("---")
st.subheader(f"📰 Live News & Sentiment for {active_symbol_for_news}")

bias, details, headlines = get_cached_news(active_symbol_for_news)
col_n1, col_n2 = st.columns([1, 2])

with col_n1:
    st.metric("Stream Status", bias)
    st.write("**Asset Feed Details**")
    st.json(details)
    
with col_n2:
    st.write(f"**Top Live Headlines for {active_symbol_for_news}**")
    if headlines:
        for h in headlines:
            st.write(f"• {h}")

time.sleep(3)
st.rerun()