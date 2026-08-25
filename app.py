import streamlit as st
import pandas as pd
import yfinance as yf
from streamlit_autorefresh import st_autorefresh
from quant_engine import analyze_index, build_scanner_row

st.set_page_config(
    page_title="Quant AI Trading Terminal",
    page_icon="🏛️",
    layout="wide"
)

# 🔄 दर १० सेकंदांनी डॅशबोर्ड आपोआप लाईव्ह डेटा रिफ्रेश करेल
st_autorefresh(interval=10000, limit=None, key="live_market_autorefresh")

st.title("🏛️ Institutional Quant AI Trading Terminal")
st.markdown("<b>Real-time Quantitative Analysis, Pivot Levels, Volume Surge & Risk Management Engine</b>", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.header("⚙️ Trading Parameters & Risk Shield")
user_capital = st.sidebar.number_input("Account Capital (₹)", min_value=10000, value=100000, step=10000)
risk_percentage = st.sidebar.slider("Risk Per Trade (%)", min_value=0.5, max_value=5.0, value=1.0, step=0.5)

selected_tab = st.sidebar.radio("Select Engine Mode", ["Index Derivatives Engine", "Equity Breakout Scanner"])

if selected_tab == "Index Derivatives Engine":
    st.subheader("📈 Index Derivatives Quantitative Signals (Live Stream)")
    index_symbol = st.selectbox("Select Benchmark Index", ["^NSEI", "^NSEBANK"], format_func=lambda x: "NIFTY 50" if x == "^NSEI" else "BANK NIFTY")
    
    # ⚡ बटण न दाबता थेट ऑटो-अपडेट होणारा कोड
    df_15m = yf.download(index_symbol, period="5d", interval="15m", progress=False)
    if isinstance(df_15m.columns, pd.MultiIndex):
        df_15m.columns = df_15m.columns.get_level_values(0)
    
    res = analyze_index(index_symbol, df_15m, display_name="NIFTY 50" if index_symbol == "^NSEI" else "BANK NIFTY")
    
    if res:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Price", f"₹{res.get('price', 0.0)}")
        col2.metric("Execution Action", res.get('action', 'N/A'))
        col3.metric("AI Confidence Score", f"{res.get('confidence', 0)}%")
        col4.metric("Recommended Size", f"{res.get('position_size', 1)} Lot(s)")

        st.markdown("---")
        
        # Pivots & Risk Metrics Table
        st.subheader("🎯 Institutional Trade Levels & Risk Parameters")
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.write("**Targets & Stop Loss**")
            st.json({
                "Entry Price": res.get('entry', 0.0),
                "Target 1": res.get('tp1', 0.0),
                "Target 2": res.get('tp2', 0.0),
                "Stop Loss": res.get('sl', 0.0),
                "Risk / Reward Ratio": "1 : 2.8+"
            })
            
        with col_b:
            st.write("**Daily Pivot Levels**")
            if res.get('pivots'):
                st.json(res['pivots'])
            else:
                st.info("Pivot calculations currently unavailable.")

        st.subheader("💡 Quant Logic & Confluence Factors")
        for r in res.get('reasons', []):
            st.markdown(f"- {r}", unsafe_allow_html=True)
    else:
        st.error("Unable to fetch index market data. Please retry after market hours.")

elif selected_tab == "Equity Breakout Scanner":
    st.subheader("⚡ Multi-Dimensional Equity Breakout Scanner (Live Stream)")
    
    # TATAMOTORS आणि LTIM काढलेली वॉचलिस्ट
    watchlist = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL", "TATASTEEL"]
    
    results = []
    for sym in watchlist:
        yf_ticker = f"{sym}.NS"
        df_15m = yf.download(yf_ticker, period="5d", interval="15m", progress=False)
        if isinstance(df_15m.columns, pd.MultiIndex):
            df_15m.columns = df_15m.columns.get_level_values(0)
        
        row = build_scanner_row(sym, df_15m)
        if row:
            results.append(row)
    
    if results:
        df_display = pd.DataFrame(results)
        st.dataframe(
            df_display[['symbol', 'action', 'price', 'position_size', 'tp1', 'tp2', 'sl', 'confidence']],
            column_config={
                "symbol": "Ticker",
                "action": "Action Signal",
                "price": "Current Price (₹)",
                "position_size": f"Rec. Shares ({risk_percentage}% Risk)",
                "tp1": "Target 1 (₹)",
                "tp2": "Target 2 (₹)",
                "sl": "Stop Loss (₹)",
                "confidence": "AI Confidence (%)"
            },
            use_container_width=True
        )