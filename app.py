import streamlit as st
import pandas as pd
from data_engine import fetch_stock_data, market_status
from quant_engine import analyze_institutional_matrix
from broker_engine import get_portfolio

st.set_page_config(page_title="Quant AI Terminal", layout="wide")
st.title("🏛️ Institutional Quant AI Terminal V2")

# ⚡ LIVE TICKER FRAGMENT (Updates every 2 seconds without full page reload)
@st.fragment(run_every="2s")
def show_live_tickers():
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

show_live_tickers()

st.markdown("---")

# Sidebar Navigation
with st.sidebar:
    st.header("Navigation & Settings")
    view_mode = st.radio("Select View", ["📈 Live Index Analysis", "💼 Paper Options & Live P&L"])
    st.info(f"Market Status: **{market_status()}**")

# VIEW 1: Live Index Analysis
if view_mode == "📈 Live Index Analysis":
    with st.sidebar:
        symbol = st.selectbox("Select Index", ["^NSEI", "^NSEBANK", "^BSESN"], index=0)
        interval = st.selectbox("Chart Interval", options=["1m", "5m", "15m", "1h"], index=1)

    if symbol:
        df = fetch_stock_data(symbol, period="5d", interval=interval)
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
            st.write("### Price Chart")
            if 'close' in df.columns:
                st.line_chart(df[['close']])

# VIEW 2: Paper Options & Real-time Live P&L
elif view_mode == "💼 Paper Options & Live P&L":
    
    # ⚡ LIVE P&L FRAGMENT (Updates every 2 seconds)
    @st.fragment(run_every="2s")
    def show_live_portfolio():
        st.subheader("💼 Options Paper Account (Live Running P&L)")
        
        portfolio = get_portfolio()
        positions = portfolio.get("positions", {})
        history = portfolio.get("history", [])
        
        total_realized_pnl = sum([item.get("pnl", 0.0) for item in history if "pnl" in item])
        
        pos_data = []
        total_unrealized_pnl = 0.0
        
        if positions:
            for sym, pos in positions.items():
                curr_price = pos['entry_price']
                
                # Robust symbol mapping logic
                if "NIFTY 50" in sym:
                    fetch_sym = "^NSEI"
                elif "BANK NIFTY" in sym:
                    fetch_sym = "^NSEBANK"
                elif "SENSEX" in sym:
                    fetch_sym = "^BSESN"
                else:
                    fetch_sym = sym
                
                try:
                    df_curr = fetch_stock_data(fetch_sym, period="1d", interval="1m")
                    if not df_curr.empty:
                        curr_price = round(float(df_curr['close'].iloc[-1]), 2)
                except Exception:
                    pass
                
                # P&L Calculation logic based on trade direction
                action = pos.get("action", "")
                if "BUY CE" in action or action == "BUY / LONG":
                    unrealized_pnl = (curr_price - pos['entry_price']) * pos['qty']
                elif "BUY PE" in action or action == "SELL / SHORT":
                    unrealized_pnl = (pos['entry_price'] - curr_price) * pos['qty']
                else:
                    unrealized_pnl = 0.0
                
                total_unrealized_pnl += unrealized_pnl
                
                pos_data.append({
                    "Instrument": sym,
                    "Action": action,
                    "Qty": pos["qty"],
                    "Entry Spot": f"₹{pos['entry_price']}",
                    "Live Spot": f"₹{curr_price}",
                    "Live P&L (₹)": round(unrealized_pnl, 2),
                    "Stop Loss": f"₹{pos['sl']}",
                    "Target": f"₹{pos['tp']}"
                })

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Virtual Cash", f"₹{portfolio.get('capital', 100000.0):,.2f}")
        m2.metric("Open Positions", len(positions))
        m3.metric("Live Running P&L", f"₹{total_unrealized_pnl:,.2f}", delta=f"{total_unrealized_pnl:.2f}")
        m4.metric("Realized P&L", f"₹{total_realized_pnl:,.2f}", delta=f"{total_realized_pnl:.2f}")
        
        st.markdown("---")
        st.write("### 📊 Active Positions")
        if pos_data:
            st.dataframe(pd.DataFrame(pos_data), use_container_width=True)
        else:
            st.info("No active open positions currently.")

        st.markdown("---")
        st.write("### 📜 Executed Trade History")
        if history:
            st.dataframe(pd.DataFrame(history)[::-1], use_container_width=True)
        else:
            st.info("No executed trade history available yet.")

    show_live_portfolio()