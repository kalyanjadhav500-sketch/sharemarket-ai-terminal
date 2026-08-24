import streamlit as st
import pandas as pd
import yfinance as yf
import streamlit.components.v1 as components

try:
    from quant_engine import build_scanner_row, analyze_index
except Exception as e:
    st.error(f"Import Error: {e}")

st.set_page_config(page_title="AI Trading Terminal", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #1e222d; padding: 12px; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ AI Quant Trading Terminal")

def get_symbols(user_input):
    clean = user_input.strip().upper().replace(" ", "")
    if clean in ["NIFTY", "NIFTY50", "NIFTY 50"]:
        return "NSE:NIFTY", "^NSEI", "NIFTY 50", True
    elif clean in ["BANKNIFTY", "BANK NIFTY"]:
        return "NSE:BANKNIFTY", "^NSEBANK", "BANK NIFTY", True
    elif clean in ["SENSEX", "BSESENSEX"]:
        return "BSE:SENSEX", "^BSESN", "SENSEX", True
    elif clean in ["INDIAVIX", "VIX"]:
        return "NSE:INDIAVIX", "^INDIAVIX", "INDIA VIX", True
        
    clean_sym = clean.replace(".NS", "").replace(".BO", "")
    return f"NSE:{clean_sym}", f"{clean_sym}.NS", clean_sym, False

def render_tradingview_chart(tv_symbol):
    container_id = f"tv_chart_{tv_symbol.replace(':', '_').replace('-', '_')}"
    html_code = f"""
    <div class="tradingview-widget-container" style="height:550px;width:100%">
      <div id="{container_id}" style="height:calc(100% - 32px);width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{tv_symbol}",
        "interval": "15",
        "timezone": "Asia/Kolkata",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "{container_id}"
      }});
      </script>
    </div>
    """
    components.html(html_code, height=560)

# --- १. मुख्य मार्केट हेडर ---
st.subheader("📊 Live Market Overview")
col1, col2, col3, col4 = st.columns(4)

@st.cache_data(ttl=30)
def fetch_indices():
    symbols = {
        "NIFTY 50": "^NSEI",
        "BANK NIFTY": "^NSEBANK",
        "SENSEX": "^BSESN",
        "INDIA VIX": "^INDIAVIX"
    }
    res = {}
    for name, sym in symbols.items():
        try:
            df = yf.download(sym, period="2d", interval="15m", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if not df.empty:
                last_p = float(df['Close'].iloc[-1])
                first_p = float(df['Close'].iloc[0])
                chg = ((last_p - first_p) / first_p) * 100
                res[name] = (last_p, chg)
        except:
            res[name] = (0.0, 0.0)
    return res

indices = fetch_indices()
cols = [col1, col2, col3, col4]
for i, (name, val) in enumerate(indices.items()):
    price, chg = val
    fmt_price = f"₹{price:,.2f}" if "VIX" not in name else f"{price:.2f}"
    cols[i].metric(label=name, value=fmt_price, delta=f"{chg:+.2f}%")

st.divider()

# --- २. Search + Chart Engine ---
st.subheader("🔍 Demat Real-Time Live Chart & AI Signal Engine")
search_input = st.text_input("कोणताही स्टॉक किंवा इंडेक्स टाका (उदा. NIFTY 50, BANK NIFTY, RELIANCE, TATAMOTORS):", value="BANK NIFTY")

if search_input:
    tv_sym, yf_sym, display_name, is_index = get_symbols(search_input)
    
    st.markdown(f"### 📈 **{tv_sym}** - Demat Live Interactive Chart")
    render_tradingview_chart(tv_sym)
    
    st.divider()
    
    st.markdown(f"### 🤖 AI Agent Signal for **{display_name}**")
    
    with st.spinner("AI Agent रिअल-टाईम प्राईस ॲक्शन विश्लेषित करत आहे..."):
        try:
            df15 = yf.download(yf_sym, period="5d", interval="15m", progress=False)
            dfd = yf.download(yf_sym, period="1mo", interval="1d", progress=False)
            
            if isinstance(df15.columns, pd.MultiIndex): df15.columns = df15.columns.get_level_values(0)
            if isinstance(dfd.columns, pd.MultiIndex): dfd.columns = dfd.columns.get_level_values(0)
            
            if is_index:
                trade_setup = analyze_index(yf_sym, df15, display_name)
            else:
                trade_setup = build_scanner_row(display_name, df15, dfd)
            
            if trade_setup:
                # सुस्पष्ट बॅनर - गोंधळ होणार नाही
                if "BEARISH" in trade_setup['trend']:
                    st.error(f"🔴 **{trade_setup['trend']}** | Action: **{trade_setup['action']}**")
                else:
                    st.success(f"🟢 **{trade_setup['trend']}** | Action: **{trade_setup['action']}**")
                
                # रो १: प्राईस आणि लेव्हल्स
                c1, c2, c3 = st.columns(3)
                c1.metric("Current Price", f"₹{trade_setup['price']}")
                c2.metric("Entry Price", f"₹{trade_setup['entry']}")
                c3.metric("Stop Loss (SL)", f"₹{trade_setup['sl']}")
                
                # रो २: टार्गेट्स आणि कॉन्फिडन्स (No Cutoff)
                c4, c5, c6 = st.columns(3)
                c4.metric("Target 1 (TP1)", f"₹{trade_setup['tp1']}")
                c5.metric("Target 2 (TP2)", f"₹{trade_setup['tp2']}")
                c6.metric("AI Confidence", f"{trade_setup['confidence']}%")
                
                st.markdown("**💡 AI Research Logic (निर्णयाची सखोल कारणे):**")
                for r in trade_setup.get('reasons', []):
                    st.write(f"• {r}")
            else:
                st.warning("डेटा लोड होण्यात अडचण येत आहे. सिम्बॉल पुन्हा तपासा.")
                
        except Exception as err:
            st.error(f"विश्लेषण करताना एरर आला: {err}")

st.divider()

# --- ३. AI Radar ---
st.subheader("🔥 Top AI Radar Watchlist")
DEFAULT_STOCKS = ["RELIANCE", "TATAMOTORS", "INFY", "HDFCBANK", "TCS", "ICICIBANK", "SBIN"]

@st.cache_data(ttl=60)
def scan_radar():
    results = []
    for ticker in DEFAULT_STOCKS:
        try:
            d15 = yf.download(f"{ticker}.NS", period="5d", interval="15m", progress=False)
            dd = yf.download(f"{ticker}.NS", period="1mo", interval="1d", progress=False)
            if isinstance(d15.columns, pd.MultiIndex): d15.columns = d15.columns.get_level_values(0)
            if isinstance(dd.columns, pd.MultiIndex): dd.columns = dd.columns.get_level_values(0)
            
            row = build_scanner_row(ticker, d15, dd)
            if row: results.append(row)
        except: pass
    return results

radar_data = scan_radar()
if radar_data:
    df_radar = pd.DataFrame(radar_data)
    show_cols = [c for c in ["symbol", "trend", "action", "confidence", "price", "sl", "tp1", "tp2"] if c in df_radar.columns]
    st.dataframe(df_radar[show_cols], use_container_width=True)