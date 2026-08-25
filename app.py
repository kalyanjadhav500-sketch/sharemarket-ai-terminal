import streamlit as st
import pandas as pd
import yfinance as yf
import time
from quant_engine import analyze_index
from broker_engine import broker_stream
from news_engine import fetch_global_market_sentiment

st.set_page_config(page_title="Quant AI Trading Terminal", layout="wide")
st.title("⚡ Quant AI Trading Terminal (Profit Shield & Signal Lock Engine)")

if "active_trade" not in st.session_state:
    st.session_state["active_trade"] = None

@st.cache_data(ttl=180)
def get_cached_news(symbol_name):
    return fetch_global_market_sentiment(symbol=symbol_name)

# Sidebar Options
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

    df_data = yf.download(idx_symbol, period="5d", interval="5m", progress=False)
    if isinstance(df_data.columns, pd.MultiIndex):
        df_data.columns = df_data.columns.get_level_values(0)

    if not df_data.empty and len(df_data) > 15:
        curr_price = df_data['Close'].iloc[-1]
        tick_data = broker_stream.fetch_live_tick(idx_symbol, current_market_price=curr_price)
        bias, details, headlines = get_cached_news(selected_index)
        ltp = tick_data.get("ltp", curr_price)

        current_trade = st.session_state["active_trade"]
        
        # Evaluate setup only if no active trade locked for current symbol
        if current_trade is None or current_trade["symbol"] != selected_index:
            signal = analyze_index(idx_symbol, df_data, display_name=selected_index, tick_data=tick_data, news_headlines=headlines)
            if signal and "BUY" in signal["action"]:
                st.session_state["active_trade"] = signal
                current_trade = signal
        else:
            signal = current_trade

        # Dynamic Profit & Risk State Machine
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
                    trade_status = "🎯 TARGET 1 HIT! PROFIT BOOKED (Trailing SL to Cost)"
                    signal["stop_loss"] = entry
                elif ltp <= sl:
                    trade_status = "🛡️ STOP LOSS HIT - EXIT TRADE TO PROTECT CAPITAL"
            elif "PUT" in signal["action"]:
                if ltp <= t2:
                    trade_status = "🎯 TARGET 2 HIT! MAX PROFIT BOOKED 🎉"
                    st.balloons()
                elif ltp <= t1:
                    trade_status = "🎯 TARGET 1 HIT! PROFIT BOOKED (Trailing SL to Cost)"
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
        col3.metric("AI Confluence Score", f"{confidence}%")
        col4.metric("Recommended Size", f"{recommended_lots} Lot(s)")

        st.markdown("---")
        st.subheader("🎯 Institutional Trade Levels & Risk Shield")

        col_left, col_right = st.columns(2)
        with col_left:
            st.write("**Targets & Dynamic Stop Loss**")
            st.json({
                "Entry Price": signal["entry_price"] if signal and "BUY" in action else "N/A",
                "Target 1 (Book Partial)": signal["target1"] if signal else "N/A",
                "Target 2 (Max Target)": signal["target2"] if signal else "N/A",
                "Active Stop Loss": signal["stop_loss"] if signal else "N/A",
                "Risk / Reward Ratio": signal["rr_ratio"] if signal else "N/A"
            })
        with col_right:
            if signal:
                st.write("**Daily Pivot & VWAP Levels**")
                st.json(signal["pivots"])
            
            if st.session_state["active_trade"] is not None:
                if st.button("🔄 Reset / Exit Trade Lock"):
                    st.session_state["active_trade"] = None
                    st.rerun()

        st.markdown("---")
        st.subheader("💡 AI Deep Study Confluence Factors")
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
        
        st.markdown(f"### 🎯 Real-Time Quant Analysis for **{clean_name}**")
        
        try:
            df_data = yf.download(stock_ticker, period="5d", interval="5m", progress=False)
            if isinstance(df_data.columns, pd.MultiIndex):
                df_data.columns = df_data.columns.get_level_values(0)
                
            if not df_data.empty and len(df_data) > 15:
                eq_price = df_data['Close'].iloc[-1]
                tick_data = broker_stream.fetch_live_tick(stock_ticker, current_market_price=eq_price)
                bias, details, headlines = get_cached_news(clean_name)
                ltp = tick_data.get("ltp", eq_price)

                current_trade = st.session_state["active_trade"]
                
                if current_trade is None or current_trade["symbol"] != clean_name:
                    signal = analyze_index(stock_ticker, df_data, display_name=clean_name, tick_data=tick_data, news_headlines=headlines)
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
                            trade_status = "🎯 TARGET 1 HIT! PROFIT BOOKED (Trailing SL to Cost)"
                            signal["stop_loss"] = entry
                        elif ltp <= sl:
                            trade_status = "🛡️ STOP LOSS HIT - EXIT TRADE TO PROTECT CAPITAL"
                    elif "PUT" in signal["action"]:
                        if ltp <= t2:
                            trade_status = "🎯 TARGET 2 HIT! MAX PROFIT BOOKED 🎉"
                            st.balloons()
                        elif ltp <= t1:
                            trade_status = "🎯 TARGET 1 HIT! PROFIT BOOKED (Trailing SL to Cost)"
                            signal["stop_loss"] = entry
                        elif ltp >= sl:
                            trade_status = "🛡️ STOP LOSS HIT - EXIT TRADE TO PROTECT CAPITAL"

                action = signal["action"] if signal else "HOLD / WAIT"
                confidence = signal["confidence"] if signal else 50

                risk_amount = (account_capital * risk_per_trade_pct) / 100
                sl_val = signal["stop_loss"] if signal else ltp * 0.99
                sl_dist = abs(ltp - sl_val) if isinstance(sl_val, (int, float)) and sl_val != 0 else (ltp * 0.0075)
                rec_shares = max(1, int(risk_amount / sl_dist))

                if "TARGET" in trade_status:
                    st.success(f"### {trade_status}")
                elif "STOP LOSS" in trade_status:
                    st.error(f"### {trade_status}")
                else:
                    st.info(f"### 🔒 Status: {trade_status}")

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Live Market Price", f"₹{round(ltp, 2)}")
                col2.metric("Execution Action", action)
                col3.metric("AI Confluence Score", f"{confidence}%")
                col4.metric("Recommended Size", f"{rec_shares} Share(s)")

                st.markdown("---")
                st.subheader("🎯 Institutional Trade Levels & Risk Shield")

                col_left, col_right = st.columns(2)
                with col_left:
                    st.write("**Targets & Dynamic Stop Loss**")
                    st.json({
                        "Entry Price": signal["entry_price"] if signal and "BUY" in action else "N/A",
                        "Target 1 (Book Partial)": signal["target1"] if signal else "N/A",
                        "Target 2 (Max Target)": signal["target2"] if signal else "N/A",
                        "Active Stop Loss": signal["stop_loss"] if signal else "N/A",
                        "Risk / Reward Ratio": signal["rr_ratio"] if signal else "N/A"
                    })
                with col_right:
                    if signal:
                        st.write("**Daily Pivot & VWAP Levels**")
                        st.json(signal["pivots"])
                    
                    if st.session_state["active_trade"] is not None:
                        if st.button("🔄 Reset / Exit Trade Lock"):
                            st.session_state["active_trade"] = None
                            st.rerun()

                st.markdown("---")
                st.subheader("💡 AI Deep Study Confluence Factors")
                if signal:
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

time.sleep(2)
st.rerun()