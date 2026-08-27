import streamlit as st
import pandas as pd
from data_engine import fetch_stock_data, market_status
from quant_engine import analyze_institutional_matrix
from broker_engine import get_portfolio

st.set_page_config(page_title="Quant AI Terminal", layout="wide")
st.title("🏛️ Institutional Quant AI Terminal V2")

# Sidebar
with st.sidebar:
    st.header("Navigation & Settings")
    view_mode = st.radio("Select View", ["📈 Live Stock Analysis", "💼 Paper Portfolio & P&L"])
    st.info(f"Market Status: **{market_status()}**")

# VIEW 1: Live Stock Analysis
if view_mode == "📈 Live Stock Analysis":
    with st.sidebar:
        symbol = st.text_input("NSE Symbol", value="^NSEI")
        interval = st.selectbox("Chart Interval", options=["5m", "15m", "1h", "1d"], index=1)

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
            st.error(f"डेटा लोड होऊ शकला नाही: {symbol}")

# VIEW 2: Paper Portfolio & P&L Dashboard
elif view_mode == "💼 Paper Portfolio & P&L":
    st.subheader("💼 Paper Trading Virtual Account")
    
    portfolio = get_portfolio()
    positions = portfolio.get("positions", {})
    history = portfolio.get("history", [])
    
    # Calculate Total Realized P&L
    total_pnl = sum([item.get("pnl", 0.0) for item in history if "pnl" in item])
    
    # Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Virtual Cash Balance", f"₹{portfolio.get('capital', 100000.0):,.2f}")
    m2.metric("Active Open Positions", len(positions))
    m3.metric("Total Realized P&L", f"₹{total_pnl:,.2f}", delta=f"{total_pnl:.2f}")
    
    st.markdown("---")
    
    # Open Positions Table
    st.write("### 📊 Active Positions")
    if positions:
        pos_data = []
        for sym, pos in positions.items():
            pos_data.append({
                "Symbol": sym,
                "Type": pos["action"],
                "Qty": pos["qty"],
                "Entry Price": f"₹{pos['entry_price']}",
                "Stop Loss": f"₹{pos['sl']}",
                "Target": f"₹{pos['tp']}",
                "Entry Time": pos["entry_time"]
            })
        st.dataframe(pd.DataFrame(pos_data), use_container_width=True)
    else:
        st.info("सध्या कोणतीही Active Position उघडी नाही.")

    st.markdown("---")
    
    # Trade History Table
    st.write("### 📜 Executed Trade History")
    if history:
        st.dataframe(pd.DataFrame(history)[::-1], use_container_width=True)
    else:
        st.info("अद्याप कोणतेही ट्रेड एक्झिक्युट झालेले नाहीत.")