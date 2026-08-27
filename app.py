import streamlit as st
import pandas as pd
from data_engine import fetch_stock_data, market_status
from quant_engine import analyze_institutional_matrix
from broker_engine import get_portfolio

st.set_page_config(page_title="Quant AI Terminal", layout="wide")

# ----------------- TOP LIVE MARKET INDICES TICKER -----------------
st.title("🏛️ Institutional Quant AI Terminal V2")

idx_col1, idx_col2, idx_col3 = st.columns(3)
try:
    nifty_df = fetch_stock_data("^NSEI", period="1d", interval="1m")
    banknifty_df = fetch_stock_data("^NSEBANK", period="1d", interval="1m")
    sensex_df = fetch_stock_data("^BSESN", period="1d", interval="1m")

    if not nifty_df.empty:
        idx_col1.metric("NIFTY 50", f"₹{nifty_df['close'].iloc[-1]:,.2f}")
    if not banknifty_df.empty:
        idx_col2.metric("BANK NIFTY", f"₹{banknifty_df['close'].iloc[-1]:,.2f}")
    if not sensex_df.empty:
        idx_col3.metric("SENSEX", f"₹{sensex_df['close'].iloc[-1]:,.2f}")
except Exception:
    pass

st.markdown("---")

# Sidebar Navigation
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

# VIEW 2: Paper Portfolio & Real-time Live P&L Dashboard
elif view_mode == "💼 Paper Portfolio & P&L":
    st.subheader("💼 Paper Trading Virtual Account (Live P&L)")
    
    portfolio = get_portfolio()
    positions = portfolio.get("positions", {})
    history = portfolio.get("history", [])
    
    total_realized_pnl = sum([item.get("pnl", 0.0) for item in history if "pnl" in item])
    
    # Process Live Open Positions and Calculate Running Live P&L
    pos_data = []
    total_unrealized_pnl = 0.0
    
    if positions:
        with st.spinner("Fetching current market prices for live P&L..."):
            for sym, pos in positions.items():
                curr_price = pos['entry_price']
                try:
                    df_curr = fetch_stock_data(sym, period="1d", interval="1m")
                    if not df_curr.empty:
                        curr_price = round(float(df_curr['close'].iloc[-1]), 2)
                except Exception:
                    pass
                
                # Live P&L Calculation
                if pos["action"] == "BUY / LONG":
                    unrealized_pnl = (curr_price - pos['entry_price']) * pos['qty']
                else:
                    unrealized_pnl = (pos['entry_price'] - curr_price) * pos['qty']
                
                total_unrealized_pnl += unrealized_pnl
                
                pos_data.append({
                    "Symbol": sym,
                    "Type": pos["action"],
                    "Qty": pos["qty"],
                    "Entry Price": f"₹{pos['entry_price']}",
                    "Live Price": f"₹{curr_price}",
                    "Live P&L (₹)": round(unrealized_pnl, 2),
                    "Stop Loss": f"₹{pos['sl']}",
                    "Target": f"₹{pos['tp']}",
                    "Entry Time": pos["entry_time"]
                })

    # Summary Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Virtual Cash", f"₹{portfolio.get('capital', 100000.0):,.2f}")
    m2.metric("Open Positions", len(positions))
    m3.metric("Live Running P&L", f"₹{total_unrealized_pnl:,.2f}", delta=f"{total_unrealized_pnl:.2f}")
    m4.metric("Realized P&L", f"₹{total_realized_pnl:,.2f}", delta=f"{total_realized_pnl:.2f}")
    
    st.markdown("---")
    
    # Active Positions Table with Live Prices
    st.write("### 📊 Active Positions (Real-time P&L)")
    if pos_data:
        st.dataframe(pd.DataFrame(pos_data), use_container_width=True)
    else:
        st.info("सध्या कोणतीही Active Position उघडी नाही.")

    st.markdown("---")
    
    # Closed Trade History
    st.write("### 📜 Executed Trade History")
    if history:
        st.dataframe(pd.DataFrame(history)[::-1], use_container_width=True)
    else:
        st.info("अद्याप कोणतेही ट्रेड पूर्ण झालेले नाहीत.")