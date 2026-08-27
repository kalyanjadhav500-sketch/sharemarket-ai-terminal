import streamlit as st
import pandas as pd
from data_engine import fetch_stock_data, market_status
from quant_engine import analyze_institutional_matrix
from broker_engine import get_portfolio

# Page Configuration
st.set_page_config(
    page_title="Institutional Quant AI Terminal V2",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Institutional Demat Look
st.markdown("""
    <style>
    .stMetric {
        background-color: #1E222D;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #2A2E39;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏛️ Institutional Quant AI Terminal V2")

# Index Configuration & Lot Size Definitions
INDEX_MAP = {
    "NIFTY 50": {"symbol": "^NSEI", "lot_size": 25},
    "BANK NIFTY": {"symbol": "^NSEBANK", "lot_size": 15},
    "SENSEX": {"symbol": "^BSESN", "lot_size": 10}
}

# ⚡ LIVE INDEX TICKERS FRAGMENT (Updates every 2s)
@st.fragment(run_every="2s")
def show_live_tickers():
    c1, c2, c3 = st.columns(3)
    try:
        nifty_df = fetch_stock_data("^NSEI", period="1d", interval="1m")
        banknifty_df = fetch_stock_data("^NSEBANK", period="1d", interval="1m")
        sensex_df = fetch_stock_data("^BSESN", period="1d", interval="1m")

        if not nifty_df.empty:
            c1.metric("NIFTY 50", f"₹{nifty_df['close'].iloc[-1]:,.2f}")
        if not banknifty_df.empty:
            c2.metric("BANK NIFTY", f"₹{banknifty_df['close'].iloc[-1]:,.2f}")
        if not sensex_df.empty:
            c3.metric("SENSEX", f"₹{sensex_df['close'].iloc[-1]:,.2f}")
    except Exception:
        pass

show_live_tickers()
st.markdown("---")

# Sidebar Setup
with st.sidebar:
    st.header("Navigation & Settings")
    view_mode = st.radio("Select View", ["📈 Live Index Quant Analysis", "💼 Live Demat Terminal & Positions"])
    st.info(f"Market Status: **{market_status()}**")

# VIEW 1: Live Index Quant Analysis (NIFTY 50, BANK NIFTY, SENSEX Only)
if view_mode == "📈 Live Index Quant Analysis":
    with st.sidebar:
        st.subheader("Index Selection")
        selected_index = st.selectbox("Select Index", list(INDEX_MAP.keys()), index=0)
        interval = st.selectbox("Chart Interval", options=["1m", "5m", "15m", "1h"], index=1)

    symbol = INDEX_MAP[selected_index]["symbol"]
    df = fetch_stock_data(symbol, period="5d", interval=interval)
    
    if not df.empty:
        res = analyze_institutional_matrix(df)
        
        st.subheader(f"Quant Matrix Scorecard: {selected_index}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Spot Price", f"₹{res['price']}")
        col2.metric("AI Signal", res['action'])
        col3.metric("AI Confidence", f"{res['confidence']}%")
        col4.metric("Market Regime", res['regime'])
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.write("### 🎯 Trade Execution Levels")
            st.write(f"🎯 **Target 1:** ₹{res['tp1']}")
            st.write(f"🎯 **Target 2:** ₹{res['tp2']}")
            st.write(f"🛑 **Stop Loss:** ₹{res['sl']}")
        
        with c2:
            st.write("### 💡 Quant Analysis Rationale")
            for reason in res['reasons']:
                st.markdown(f"• {reason}")

        st.markdown("---")
        st.write("### Real-Time Spot Chart")
        if 'close' in df.columns:
            st.line_chart(df[['close']])

# VIEW 2: Institutional Live Demat Terminal
elif view_mode == "💼 Live Demat Terminal & Positions":
    
    @st.fragment(run_every="2s")
    def render_demat_account():
        st.subheader("💼 Live Demat Trading Account (Paper Trading)")
        
        portfolio = get_portfolio()
        positions = portfolio.get("positions", {})
        history = portfolio.get("history", [])
        
        total_realized_pnl = sum([item.get("pnl", 0.0) for item in history if "pnl" in item])
        
        # Categorized positions containers
        nifty_pos, banknifty_pos, sensex_pos, other_pos = [], [], [], []
        total_unrealized_pnl = 0.0

        if positions:
            for sym, pos in positions.items():
                # Detect target Index mapping & Lot size
                if "NIFTY 50" in sym or "^NSEI" in sym:
                    fetch_sym = "^NSEI"
                    category = "NIFTY 50"
                    lot_size = INDEX_MAP["NIFTY 50"]["lot_size"]
                elif "BANK NIFTY" in sym or "^NSEBANK" in sym:
                    fetch_sym = "^NSEBANK"
                    category = "BANK NIFTY"
                    lot_size = INDEX_MAP["BANK NIFTY"]["lot_size"]
                elif "SENSEX" in sym or "^BSESN" in sym:
                    fetch_sym = "^BSESN"
                    category = "SENSEX"
                    lot_size = INDEX_MAP["SENSEX"]["lot_size"]
                else:
                    fetch_sym = sym
                    category = "OTHER"
                    lot_size = 1

                curr_price = pos['entry_price']
                try:
                    df_curr = fetch_stock_data(fetch_sym, period="1d", interval="1m")
                    if not df_curr.empty:
                        curr_price = round(float(df_curr['close'].iloc[-1]), 2)
                except Exception:
                    pass

                action = pos.get("action", "")
                qty = pos.get("qty", 1)
                lots = max(1, qty // lot_size) if lot_size > 1 else qty

                # Calculate unrealized P&L
                if "BUY" in action or "LONG" in action or "BUY CE" in action:
                    unrealized_pnl = (curr_price - pos['entry_price']) * qty
                else:
                    unrealized_pnl = (pos['entry_price'] - curr_price) * qty
                
                total_unrealized_pnl += unrealized_pnl

                row_data = {
                    "Instrument": sym,
                    "Action": action,
                    "Lots / Qty": f"{lots} Lot(s) ({qty} Qty)",
                    "Entry Spot": f"₹{pos['entry_price']}",
                    "Live Spot (LTP)": f"₹{curr_price}",
                    "Stop Loss": f"₹{pos['sl']}",
                    "Target": f"₹{pos['tp']}",
                    "Live P&L (₹)": round(unrealized_pnl, 2)
                }

                if category == "NIFTY 50":
                    nifty_pos.append(row_data)
                elif category == "BANK NIFTY":
                    banknifty_pos.append(row_data)
                elif category == "SENSEX":
                    sensex_pos.append(row_data)
                else:
                    other_pos.append(row_data)

        # Overview Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Available Capital", f"₹{portfolio.get('capital', 100000.0):,.2f}")
        m2.metric("Active Positions", len(positions))
        m3.metric("Live Unrealized P&L", f"₹{total_unrealized_pnl:,.2f}", delta=f"{total_unrealized_pnl:.2f}")
        m4.metric("Realized P&L", f"₹{total_realized_pnl:,.2f}", delta=f"{total_realized_pnl:.2f}")

        st.markdown("---")
        st.subheader("📌 Active Index Positions")

        # Categorized Tabs for separate detailed views
        tab_all, tab_nifty, tab_banknifty, tab_sensex = st.tabs([
            "📋 All Active Positions", 
            "📈 NIFTY 50", 
            "🏦 BANK NIFTY", 
            "📊 SENSEX"
        ])

        with tab_all:
            all_pos = nifty_pos + banknifty_pos + sensex_pos + other_pos
            if all_pos:
                st.dataframe(pd.DataFrame(all_pos), use_container_width=True)
            else:
                st.info("No active open positions currently.")

        with tab_nifty:
            if nifty_pos:
                st.dataframe(pd.DataFrame(nifty_pos), use_container_width=True)
            else:
                st.info("No active positions in NIFTY 50.")

        with tab_banknifty:
            if banknifty_pos:
                st.dataframe(pd.DataFrame(banknifty_pos), use_container_width=True)
            else:
                st.info("No active positions in BANK NIFTY.")

        with tab_sensex:
            if sensex_pos:
                st.dataframe(pd.DataFrame(sensex_pos), use_container_width=True)
            else:
                st.info("No active positions in SENSEX.")

        st.markdown("---")
        st.subheader("📜 Executed Order History")
        if history:
            st.dataframe(pd.DataFrame(history)[::-1], use_container_width=True)
        else:
            st.info("No trade history recorded yet.")

    render_demat_account()