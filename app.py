import streamlit as st
import pandas as pd
from data_engine import fetch_stock_data, market_status
from quant_engine import analyze_institutional_matrix

st.set_page_config(page_title="Quant AI Terminal", layout="wide")
st.title("🏛️ Institutional Quant AI Terminal V2")

with st.sidebar:
    st.header("Navigation & Settings")
    symbol = st.text_input("NSE Symbol", value="^NSEI")
    interval = st.selectbox("Chart Interval", options=["5m", "15m", "1h", "1d"], index=1)
    st.info(f"Market Status: **{market_status()}**")

if symbol:
    df = fetch_stock_data(symbol, period="1mo", interval=interval)
    
    if not df.empty:
        res = analyze_institutional_matrix(df)
        
        st.subheader(f"Quant Matrix Scorecard: {symbol}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Price", f"₹{res['price']}")
        col2.metric("Signal Action", res['action'])
        col3.metric("AI Confidence", f"{res['confidence']}%")
        col4.metric("Market Regime", res['regime'])
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("### Target & Risk Setup")
            st.write(f"🎯 **Target 1:** ₹{res['tp1']}")
            st.write(f"🎯 **Target 2:** ₹{res['tp2']}")
            st.write(f"🛑 **Stop Loss:** ₹{res['sl']}")
        
        with c2:
            st.write("### 💡 Quant Rationale")
            for reason in res['reasons']:
                st.markdown(f"• {reason}")

        st.markdown("---")
        st.write("### Price Chart (Close vs EMA 20)")
        if 'close' in df.columns and 'ema_20' in df.columns:
            st.line_chart(df[['close', 'ema_20']])
        elif 'close' in df.columns:
            st.line_chart(df[['close']])
    else:
        st.error(f"डेटा लोड होऊ शकला नाही: {symbol}. कृपया योग्य सिम्बॉल टाका.")