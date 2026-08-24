import streamlit as st
import pandas as pd
import yfinance as yf
import streamlit.components.v1 as components

# Quant Engine इंपोर्ट
try:
    from quant_engine import build_scanner_row
except Exception as e:
    st.error(f"Import Error: {e}")

st.set_page_config(page_title="AI Trading Terminal", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #1e222d; padding: 12px; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ AI Quant Trading Terminal")

def get_tv_symbol(user_input):
    """TradingView चा अचूक Symbol शोधणे"""
    clean = user_input.strip().upper().replace(" ", "")
    tv_map = {
        "NIFTY": "NSE:NIFTY",
        "NIFTY50": "NSE:NIFTY",
        "BANKNIFTY": "NSE:BANKNIFTY",
        "FINNIFTY": "NSE:FINNIFTY",
        "SENSEX": "BSE:SENSEX",
        "INDIAVIX": "NSE:INDIAVIX",
        "VIX": "NSE:INDIAVIX"
    }
    if clean in tv_map:
        return tv_map[clean]
    
    clean_sym = clean.replace(".NS", "").replace(".BO", "")
    return f"NSE:{clean_sym}"

def get_yf_symbol(user_input):
    """Yahoo Finance चा सिम्बॉल"""
    clean = user_input.strip().upper()
    yf_map = {
        "NIFTY": "^NSEI",
        "NIFTY 50": "^NSEI",
        "NIFTY50": "^NSEI",
        "BANK NIFTY": "^NSEBANK",
        "BANKNIFTY": "^NSEBANK",
        "SENSEX": "^BSESN",
        "INDIA VIX": "^INDIAVIX"
    }
    if clean in yf_map:
        return yf_map[clean]
    clean_stock = clean.replace(" ", "").replace(".NS", "").replace(".BO", "")
    return clean_stock + ".NS"

def render_tradingview_chart(tv_symbol):
    """Demat ॲपसारखा Full Live TradingView Chart Widget"""
    html_code = f"""
    <div class="tradingview-widget-container" style="height:550px;width:100%">
      <div id="tradingview_chart_element" style="height:calc(100% - 32px);width:100%"></div>
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
        "container_id": "tradingview_chart_element"
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

# --- २. Universal Search + Demat Live Chart Engine ---
st.subheader("🔍 Demat Real-Time Live Chart & AI Signal Engine")
search_input = st.text_input("कोणताही स्टॉक किंवा इंडेक्स टाका (उदा. NIFTY 50, BANK NIFTY, RELIANCE, TATAMOTORS, INFY):", value="NIFTY 50")

if search_input:
    tv_sym = get_tv_symbol(search_input)
    yf_sym = get_yf_symbol(search_input)
    display_name = search_input.strip().upper()
    
    st.markdown(f"### 📈 **{tv_sym}** - Demat Live Interactive Chart")
    render_tradingview_chart(tv_sym)
    
    st.divider()
    
    st.markdown(f"### 🤖 AI Agent Deep Research Analysis for **{display_name}**")
    
    with st.spinner("AI Agent बाजाराचे तांत्रिक व न्यूज विश्लेषण करत आहे..."):
        try:
            df15 = yf.download(yf_sym, period="5d", interval="15m", progress=False)
            dfd = yf.download(yf_sym, period="1mo", interval="1d", progress=False)
            
            if isinstance(df15.columns, pd.MultiIndex): df15.columns = df15.columns.get_level_values(0)
            if isinstance(dfd.columns, pd.MultiIndex): dfd.columns = dfd.columns.get_level_values(0)
            
            trade_setup = build_scanner_row(display_name, df15, dfd)
            
            if trade_setup:
                action_emoji = "🟢 BUY / CALL" if "BUY" in trade_setup['action'] else "🔴 SELL / PUT"
                st.markdown(f"#### AI Trade Recommendation: **{action_emoji}**")
                
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Current Price", f"₹{trade_setup['price']}")
                m2.metric("Action", trade_setup['action'])
                m3.metric("Entry Price", f"₹{trade_setup['entry']}")
                m4.metric("Stop Loss (SL)", f"₹{trade_setup['sl']}")
                m5.metric("Target 1 / 2", f"₹{trade_setup['tp1']} / ₹{trade_setup['tp2']}")
                
                st.write(f"**AI Confidence Level:** `{trade_setup['confidence']}%`")
                st.markdown("**💡 AI Research Logic (निर्णयाची सखोल कारणे):**")
                for r in trade_setup['reasons']:
                    st.write(f"• {r}")
            else:
                st.warning("या स्टॉकचा रिअल-टाईम डेटा लोड होण्यात अडचण येत आहे. कृपया सिम्बॉल पुन्हा तपासा.")
                
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
    show_cols = [c for c in ["symbol", "action", "confidence", "price", "sl", "tp1", "tp2"] if c in df_radar.columns]
    st.dataframe(df_radar[show_cols], use_container_width=True)