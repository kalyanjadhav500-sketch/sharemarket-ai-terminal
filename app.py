import streamlit as st
import pandas as pd
import yfinance as yf
import time
from quant_engine import analyze_institutional_matrix
from broker_engine import broker_stream
from news_engine import fetch_global_market_sentiment

st.set_page_config(page_title="Quant AI Trading Terminal", layout="wide")
st.title("⚡ Quant AI Trading Terminal (Institutional Multi-Timeframe Matrix)")

if "active_trade" not in st.session_state:
    st.session_state["active_trade"] = None

@st.cache_data(ttl=180)
def get_cached_news(symbol_name):
    return fetch_global_market_sentiment(symbol=symbol_name)

st.sidebar.header("⚙️ Institutional Parameters & Risk Shield")
account_capital = st.sidebar.number_input("Account Capital (₹)", value=100000, step=10000)
risk_per_trade_pct = st.sidebar.slider("Risk Per Trade (%)", 0.5, 3.0, 1.0, 0.1)

engine_mode = st.sidebar.radio("Select Engine Mode", ["Index Derivatives Engine", "Equity Stock Search Engine"])
active_symbol_for_news = "BANK NIFTY"

if engine_mode == "Index Derivatives Engine":
    selected_index = st.selectbox("Select Benchmark Index", ["BANK NIFTY", "NIFTY 50"])
    symbol_map = {"BANK NIFTY": "^NSEBANK", "NIFTY 50": "^NSEI"}
    heavyweight_map = {"BANK NIFTY": "HDFCBANK.NS", "NIFTY 50": "RELIANCE.NS"}
    
    idx_symbol = symbol_map[selected_index]
    hw_symbol = heavyweight_map[selected_index]
    active_symbol_for_news = selected_index

    # Fetch Multi-Timeframe Data
    df_daily = yf.download(idx_symbol, period="10d", interval="1d", progress=False)
    df_15m = yf.download(idx_symbol, period="5d", interval="15m", progress=False)
    df_5m = yf.download(idx_symbol, period="5d", interval="5m", progress=False)
    
    # Fetch VIX & Heavyweight Data
    df_vix = yf.download("^INDIAVIX", period="5d", interval="1d", progress=False)
    df_hw = yf.download(hw_symbol, period="5d", interval="1d", progress=False)

    for df in [df_daily, df_15m, df_5m, df_vix, df_hw]:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

    if not df_5m.empty and len(df_5m) > 15:
        curr_price = df_5m['Close'].iloc[-1]
        tick_data = broker_stream.fetch_live_tick(idx_symbol, current_market_price=curr_price)
        bias, details, headlines = get_cached_news(selected_index)
        ltp = tick_data.get("ltp", curr_price)

        current_trade = st.session_state["active_trade"]
        
        if current_trade is None or current_trade["symbol"] != selected_index:
            signal = analyze_institutional_matrix(
                symbol=idx_symbol,
                df_5m=df_5m,
                df_15m=df_15m,
                df_daily=df_daily,
                df_vix=df_vix,
                df_heavyweight=df_hw,
                display_name=selected_index,
                tick_data=tick_data,
                news_headlines=headlines
            )
            if signal and "BUY" in signal["action"]:
                st.session_state["active_trade"] = signal
                current_trade = signal
        else:
            signal = current_trade

        trade_status = "ACTIVE TRADE LOCKED"
        if signal and "BUY" in signal["action"]:
            entry = signal["entry_price"]
            t1 = signal["target1"]
            t2 = signal["target2"]
            sl = signal["stop_loss"]

            if "CALL" in signal["action"]:
                if ltp >= t2:
                    trade_status = "🎯 TARGET 2 HIT! MAX PROFIT BOOKED 🎉"
                    st.balloons()
                elif ltp >= t1:
                    trade_status = "🎯 TARGET 1 HIT! TRAILING SL ACTIVE"
                    signal["stop_loss"] = entry
                elif ltp <= sl:
                    trade_status = "🛡️ STOP LOSS HIT - EXIT TRADE TO PROTECT CAPITAL"
            elif "PUT" in signal["action"]:
                if ltp <= t2:
                    trade_status = "🎯 TARGET 2 HIT! MAX PROFIT BOOKED 🎉"
                    st.balloons()
                elif ltp <= t1:
                    trade_status = "🎯 TARGET 1 HIT! TRAILING SL ACTIVE"
                    signal["stop_loss"] = entry
                elif ltp >= sl:
                    trade_status = "🛡️ STOP LOSS HIT - EXIT TRADE TO PROTECT CAPITAL"

        action = signal["action"] if signal else "HOLD / WAIT"
        confidence = signal["confidence"] if signal else 50

        lot_size_map = {"BANK NIFTY": 15, "NIFTY 50": 25}
        risk_amount = (account_capital * risk_per_trade_pct) / 100
        recommended_lots = max(1, int(risk_amount / (lot_size_map[selected_index] * 50)))

        if "TARGET" in trade_status:
            st.success(f"### {trade_status}")
        elif "STOP LOSS" in trade_status:
            st.error(f"### {trade_status}")
        else:
            st.info(f"### 🔒 Status: {trade_status}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Live Market Price", f"₹{round(ltp, 2)}")
        col2.metric("Execution Action", action)
        col3.metric("Multi-TF Score", f"{confidence}%")
        col4.metric("Recommended Size", f"{recommended_lots} Lot(s)")

        st.markdown("---")
        st.subheader("🎯 Locked Trade Levels & Risk Shield")

        col_left, col_right = st.columns(2)
        with col_left:
            st.write("**Targets & Dynamic Stop Loss**")
            st.json({
                "Entry Price": signal["entry_price"] if signal and "BUY" in action else "N/A",
                "Target 1": signal["target1"] if signal else "N/A",
                "Target 2": signal["target2"] if signal else "N/A",
                "Active Stop Loss": signal["stop_loss"] if signal else "N/A",
                "Risk / Reward Ratio": signal["rr_ratio"] if signal else "N/A"
            })
        with col_right:
            if signal:
                st.write("**Institutional Key Levels (VWAP & PDH/PDL)**")
                st.json(signal["pivots"])
            
            if st.session_state["active_trade"] is not None:
                if st.button("🔄 Reset Active Signal Lock"):
                    st.session_state["active_trade"] = None
                    st.rerun()

        st.markdown("---")
        st.subheader("💡 Institutional Confluence Reasoning")
        if signal:
            for reason in signal["reasons"]:
                st.write(f"• {reason}")

elif engine_mode == "Equity Stock Search Engine":
    st.subheader("🔍 Dynamic Equity Stock Search")
    user_stock = st.text_input("🔍 Type Stock Symbol (e.g. RELIANCE, TATAMOTORS, SBIN):", value="RELIANCE").upper().strip()
    
    if user_stock:
        stock_ticker = f"{user_stock}.NS" if not user_stock.endswith(".NS") else user_stock
        clean_name = user_stock.replace(".NS", "")
        active_symbol_for_news = clean_name
        
        try:
            df_daily = yf.download(stock_ticker, period="10d", interval="1d", progress=False)
            df_15m = yf.download(stock_ticker, period="5d", interval="15m", progress=False)
            df_5m = yf.download(stock_ticker, period="5d", interval="5m", progress=False)

            for df in [df_daily, df_15m, df_5m]:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

            if not df_5m.empty and len(df_5m) > 15:
                eq_price = df_5m['Close'].iloc[-1]
                tick_data = broker_stream.fetch_live_tick(stock_ticker, current_market_price=eq_price)
                bias, details, headlines = get_cached_news(clean_name)
                ltp = tick_data.get("ltp", eq_price)

                signal = analyze_institutional_matrix(
                    symbol=stock_ticker,
                    df_5m=df_5m,
                    df_15m=df_15m,
                    df_daily=df_daily,
                    display_name=clean_name,
                    tick_data=tick_data,
                    news_headlines=headlines
                )

                action = signal["action"] if signal else "HOLD / WAIT"
                confidence = signal["confidence"] if signal else 50

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Live Price", f"₹{round(ltp, 2)}")
                col2.metric("Action", action)
                col3.metric("Confluence Score", f"{confidence}%")
                col4.metric("Risk Status", "Calculated")

                st.markdown("---")
                if signal:
                    st.subheader("🎯 Stock Analysis Details")
                    st.json({
                        "Entry Price": signal["entry_price"],
                        "Target 1": signal["target1"],
                        "Target 2": signal["target2"],
                        "Stop Loss": signal["stop_loss"]
                    })
        except Exception as e:
            st.error(f"⚠️ Error fetching stock data: {e}")

st.markdown("---")
st.subheader(f"📰 Live News & Sentiment for {active_symbol_for_news}")

bias, details, headlines = get_cached_news(active_symbol_for_news)
col_n1, col_n2 = st.columns([1, 2])

with col_n1:
    st.metric("Stream Status", bias)
    st.write("**Feed Details**")
    st.json(details)
    
with col_n2:
    st.write("**Top Live Headlines**")
    if headlines:
        for h in headlines:
            st.write(f"• {h}")

time.sleep(2)
st.rerun()