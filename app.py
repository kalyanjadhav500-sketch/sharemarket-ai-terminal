import streamlit as st
import pandas as pd
import yfinance as yf
import time

# Quant Engine इंपोर्ट
try:
    from quant_engine import add_indicators, build_scanner_row
except Exception as e:
    st.error(f"Import Error: {e}")

st.set_page_config(page_title="AI Trading Terminal", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #1e222d; padding: 12px; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ AI Quant Trading Terminal")

def resolve_symbol(user_input):
    """कोणतेही नाव (NIFTY 50, Bank Nifty, Stock Name) Yahoo Ticker मध्ये बदलणे"""
    clean = user_input.strip().upper()
    
    # इंडेक्स मॅपिंग (इंडेक्स कोड फिक्सिंग)
    index_map = {
        "NIFTY": "^NSEI",
        "NIFTY 50": "^NSEI",
        "NIFTY50": "^NSEI",
        "BANK NIFTY": "^NSEBANK",
        "BANKNIFTY": "^NSEBANK",
        "SENSEX": "^BSESN",
        "BSE SENSEX": "^BSESN",
        "INDIA VIX": "^INDIAVIX",
        "VIX": "^INDIAVIX",
        "INDIAVIX": "^INDIAVIX"
    }
    
    if clean in index_map:
        return index_map[clean], clean
    
    # स्टॉकच्या नावातील स्पेस काढून `.NS` जोडणे (उदा. TATA MOTORS -> TATAMOTORS.NS)
    clean_stock = clean.replace(" ", "")
    if not clean_stock.endswith(".NS") and not clean_stock.endswith(".BO") and not clean_stock.startswith("^"):
        return clean_stock + ".NS", clean_stock
    return clean_stock, clean_stock

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

# --- साइडबार ---
st.sidebar.header("⚙️ Dashboard Controls")
auto_refresh = st.sidebar.checkbox("🔄 Auto Refresh (Every 30s)", value=True)
min_conf = st.sidebar.slider("Min AI Conviction (%)", 50, 90, 60)

# --- २. Universal Smart Stock/Index Search Engine ---
st.subheader("🔍 Stock & Index AI Deep Research Engine")
search_input = st.text_input("कोणताही स्टॉक किंवा इंडेक्स टाईप करा (उदा. NIFTY 50, BANK NIFTY, RELIANCE, TATA MOTORS, INFY):", value="NIFTY 50")

if search_input:
    yf_sym, display_name = resolve_symbol(search_input)
    
    with st.spinner(f"AI Agent {display_name} वर सखोल अभ्यास करत आहे..."):
        try:
            df15 = yf.download(yf_sym, period="5d", interval="15m", progress=False)
            dfd = yf.download(yf_sym, period="1mo", interval="1d", progress=False)
            
            if isinstance(df15.columns, pd.MultiIndex): df15.columns = df15.columns.get_level_values(0)
            if isinstance(dfd.columns, pd.MultiIndex): dfd.columns = dfd.columns.get_level_values(0)
            
            if df15.empty:
                st.warning(f"⚠️ {display_name} साठी डेटा सापडला नाही. स्पेलिंग तपासा.")
            else:
                trade_setup = build_scanner_row(display_name, df15, dfd)
                
                if trade_setup is None:
                    st.info(f"🤖 **AI Decision for {display_name}:** **NEUTRAL / NO TRADE**\n\n*कारण: सध्या बाजारात रिस्क-रिवॉर्ड रेशो योग्य नाही किंवा सेंटीमेंट न्यूट्रल आहे. AI बळजबरीने कॉल देणार नाही.*")
                else:
                    action_emoji = "🟢 BUY" if trade_setup.get('action') == "BUY" else "🔴 SELL"
                    st.markdown(f"### सिग्नल: **{action_emoji}** ({display_name})")
                    
                    m1, m2, m3, m4, m5 = st.columns(5)
                    m1.metric("Current Price", f"₹{trade_setup.get('price')}")
                    m2.metric("Action", trade_setup.get('action'))
                    m3.metric("Entry Level", f"₹{trade_setup.get('entry')}")
                    m4.metric("Stop Loss (SL)", f"₹{trade_setup.get('sl')}")
                    m5.metric("Target 1 / 2", f"₹{trade_setup.get('tp1')} / ₹{trade_setup.get('tp2')}")
                    
                    st.write(f"**AI Confidence Level:** `{trade_setup.get('confidence')}%`")
                    st.markdown("**💡 AI Deep Research Analysis (निर्णयाची कारणे):**")
                    for r in trade_setup.get('reasons', []):
                        st.write(f"• {r}")
        except Exception as err:
            st.error(f"एनालिसिस करताना एरर आला: {err}")

st.divider()

# --- ३. AI वॉचलिस्ट / टॉप स्कॅनर कॉल्स ---
st.subheader("🔥 Top High-Conviction AI Radar")

DEFAULT_STOCKS = ["RELIANCE.NS", "TATAMOTORS.NS", "INFY.NS", "HDFCBANK.NS", "TCS.NS", "ICICIBANK.NS", "SBIN.NS"]

@st.cache_data(ttl=60)
def scan_radar():
    results = []
    for ticker in DEFAULT_STOCKS:
        try:
            d15 = yf.download(ticker, period="5d", interval="15m", progress=False)
            dd = yf.download(ticker, period="1mo", interval="1d", progress=False)
            if isinstance(d15.columns, pd.MultiIndex): d15.columns = d15.columns.get_level_values(0)
            if isinstance(dd.columns, pd.MultiIndex): dd.columns = dd.columns.get_level_values(0)
            
            name = ticker.replace(".NS", "")
            row = build_scanner_row(name, d15, dd)
            if row:
                results.append(row)
        except:
            pass
    return results

radar_data = scan_radar()

if radar_data:
    df_radar = pd.DataFrame(radar_data)
    if 'confidence' in df_radar.columns:
        df_radar = df_radar[df_radar['confidence'] >= min_conf]
    
    show_cols = [c for c in ["symbol", "sector", "action", "confidence", "price", "sl", "tp1", "tp2"] if c in df_radar.columns]
    st.dataframe(df_radar[show_cols], use_container_width=True)
else:
    st.info("सध्या कोणत्याही स्टॉकमध्ये हाय-कॉन्व्हिक्शन ट्रेड उपलब्ध नाही. AI रिस्क मॅनेजमेंटनुसार वेट अँड वॉच मोड चालू आहे.")

# Auto Refresh
if auto_refresh:
    time.sleep(30)
    st.rerun()