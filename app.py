import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import SETTINGS, INDICES, SECTOR_INDICES, WATCHLIST
from data_engine import fetch_history, fetch_many, market_status
from quant_engine import add_indicators, market_regime, sector_strength, build_scanner_row
from backtest_engine import backtest_vwap_momentum
from storage import init_db, save_signal, read_signals
from telegram_alerts import send_telegram_signal

st.set_page_config(page_title=SETTINGS.app_title, page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
init_db()

st.markdown("""
<style>
.stApp{background:#080b11;color:#e8edf5}
section[data-testid="stSidebar"]{background:#0d111a}
.block-container{padding-top:1.2rem;max-width:1600px}
.metric-card{background:#111722;border:1px solid #263041;border-radius:14px;padding:14px}
.signal-buy{border:1px solid #16c784;background:rgba(22,199,132,.10);border-radius:14px;padding:18px}
.signal-sell{border:1px solid #ea3943;background:rgba(234,57,67,.10);border-radius:14px;padding:18px}
.signal-neutral{border:1px solid #697386;background:rgba(105,115,134,.08);border-radius:14px;padding:18px}
.small{color:#8f9bad;font-size:.82rem}
</style>
""",unsafe_allow_html=True)

def money(v):
    return f"₹{v:,.2f}" if isinstance(v,(int,float)) else "N/A"

@st.cache_data(ttl=30, show_spinner=False)
def cached_history(symbol,period,interval):
    return fetch_history(symbol,period,interval)

@st.cache_data(ttl=45, show_spinner=False)
def cached_scan():
    nifty=cached_history(INDICES["NIFTY 50"],"6mo","1d")
    regime=market_regime(nifty)
    frames=fetch_many(WATCHLIST,"5d","15m",workers=8)
    rows=[]
    for s,df in frames.items():
        row=build_scanner_row(s,df,regime,50,"N/A")
        if row: rows.append(row)
    return pd.DataFrame(rows),regime

st.sidebar.title("⚙️ Terminal Controls")
refresh=st.sidebar.checkbox("Live Refresh",True)
if refresh:
    st.caption("Refresh the browser to request a fresh free-data snapshot. No paid feed is used.")
min_score=st.sidebar.slider("Minimum conviction",60,95,SETTINGS.min_signal_score)
capital=st.sidebar.number_input("Paper capital (₹)",100000,100000000,1000000,10000)
risk_pct=st.sidebar.slider("Risk per trade (%)",0.1,2.0,SETTINGS.default_risk_pct,0.1)
page=st.sidebar.radio("Terminal",[
    "Command Center","Market Radar","Stock Intelligence","Sector Rotation",
    "Backtesting","Signal History","Paper Risk"
])

# Header
status=market_status()
st.title("🛡️ Institutional Quant Terminal V2")
st.markdown(f"<span class='small'>FREE-DATA MODE • Market: <b>{status}</b> • Quantitative decision support, not guaranteed prediction</span>",unsafe_allow_html=True)

idx_cols=st.columns(4)
for col,(name,sym) in zip(idx_cols,INDICES.items()):
    if name=="INDIA VIX":
        df=cached_history(sym,"5d","1d")
    else:
        df=cached_history(sym,"5d","5m")
    if df.empty:
        col.metric(name,"N/A")
    else:
        last=float(df["Close"].iloc[-1]); prev=float(df["Close"].iloc[-2]) if len(df)>1 else last
        col.metric(name,money(last),f"{last-prev:+.2f}")

scan,regime=cached_scan()
if not scan.empty:
    top=scan.sort_values("confidence",ascending=False).iloc[0]
else:
    top=None

if page=="Command Center":
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Market Regime",regime["regime"])
    c2.metric("Regime Score",f"{regime['score']}/100")
    c3.metric("Bull Bias",f"{regime['bull']}/100")
    c4.metric("Bear Bias",f"{regime['bear']}/100")
    st.divider()

    st.subheader("🔥 Top Alpha Radar")
    if not scan.empty:
        show=scan.sort_values("confidence",ascending=False).head(10)
        st.dataframe(show[["symbol","sector","price","confidence","bull_score","bear_score","smart_money","rel_volume","rsi","adx","action","rr"]],use_container_width=True,hide_index=True)
    else:
        st.warning("No free-data results available right now.")

    st.subheader("🎯 Best Current Setup")
    if top is not None and top["confidence"]>=min_score and top["action"]!="NO TRADE" and top["rr"]>=SETTINGS.min_rr:
        cls="signal-buy" if top["action"]=="BUY" else "signal-sell"
        st.markdown(f"""<div class="{cls}">
        <h2>{top['action']} — {top['symbol']} <span style="float:right">{top['confidence']}/100</span></h2>
        <p><b>Entry:</b> {money(top['entry_low'])} – {money(top['entry_high'])}
        &nbsp;&nbsp; <b>SL:</b> {money(top['sl'])}
        &nbsp;&nbsp; <b>TP1:</b> {money(top['tp1'])}
        &nbsp;&nbsp; <b>TP2:</b> {money(top['tp2'])}
        &nbsp;&nbsp; <b>R:R:</b> 1:{top['rr']}</p>
        <p>Regime: {top['regime']} • Smart Money Proxy: {top['smart_money']}/100 • Relative Volume: {top['rel_volume']}x</p>
        </div>""",unsafe_allow_html=True)
        if st.button("📲 Send Top Signal to Telegram"):
            sid=save_signal(top)
            ok,msg=send_telegram_signal(top)
            st.success(f"Signal {sid} sent." if ok else f"Telegram not sent: {msg}")
    else:
        st.markdown("<div class='signal-neutral'><h2>🟡 NO TRADE</h2><p>No setup currently clears the configured conviction and R:R filters.</p></div>",unsafe_allow_html=True)

elif page=="Market Radar":
    st.subheader("📡 Market Radar")
    if not scan.empty:
        st.dataframe(scan.sort_values("confidence",ascending=False),use_container_width=True,hide_index=True)
    else: st.info("No data.")

elif page=="Stock Intelligence":
    ticker=st.text_input("NSE symbol","RELIANCE")
    symbol=ticker.upper().replace(".NS","")+".NS"
    frames={tf:cached_history(symbol,*args) for tf,args in {"5m":("5d","5m"),"15m":("1mo","15m"),"1h":("3mo","1h"),"1d":("2y","1d")}.items()}
    df=frames["15m"]
    if df.empty:
        st.error("No free market data returned for this symbol.")
    else:
        x=add_indicators(df)
        l=x.iloc[-1]
        r=market_regime(frames["1d"]) if not frames["1d"].empty else {"regime":"N/A"}
        m=build_scanner_row(symbol,df,r,50,"N/A")
        a,b,c,d,e,f=st.columns(6)
        a.metric("Price",money(m["price"])); b.metric("RSI",m["rsi"]); c.metric("VWAP",money(m["vwap"]))
        d.metric("ADX",m["adx"]); e.metric("Rel Volume",f"{m['rel_volume']}x"); f.metric("Signal",m["action"])
        st.subheader("Multi-Timeframe")
        mt=[]
        for tf,frame in frames.items():
            state=__import__("quant_engine").timeframe_state(frame)
            mt.append({"Timeframe":tf,"State":state["state"],"Bull":state.get("bull",50),"Bear":state.get("bear",50)})
        st.dataframe(pd.DataFrame(mt),use_container_width=True,hide_index=True)

        fig=make_subplots(rows=3,cols=1,shared_xaxes=True,row_heights=[.65,.2,.15],vertical_spacing=.03)
        fig.add_trace(go.Candlestick(x=x.index,open=x.Open,high=x.High,low=x.Low,close=x.Close,name="Price"),row=1,col=1)
        for col,name in [("VWAP","VWAP"),("EMA_9","EMA 9"),("EMA_21","EMA 21"),("EMA_50","EMA 50"),("EMA_200","EMA 200")]:
            fig.add_trace(go.Scatter(x=x.index,y=x[col],name=name,mode="lines"),row=1,col=1)
        fig.add_trace(go.Bar(x=x.index,y=x.Volume,name="Volume"),row=2,col=1)
        fig.add_trace(go.Scatter(x=x.index,y=x.RSI,name="RSI"),row=3,col=1)
        fig.update_layout(template="plotly_dark",height=760,xaxis_rangeslider_visible=False,margin=dict(l=10,r=10,t=20,b=10))
        st.plotly_chart(fig,use_container_width=True)

elif page=="Sector Rotation":
    st.subheader("🔄 Sector Rotation")
    frames=fetch_many(list(SECTOR_INDICES.values()),"3mo","1d",workers=5)
    sector_frames={n:frames.get(s,pd.DataFrame()) for n,s in SECTOR_INDICES.items()}
    sec=sector_strength(sector_frames)
    if sec.empty: st.warning("Sector data unavailable.")
    else:
        st.dataframe(sec,use_container_width=True,hide_index=True)
        st.bar_chart(sec.set_index("sector")["return_pct"])

elif page=="Backtesting":
    st.subheader("🧪 Free Local Backtesting")
    ticker=st.text_input("Backtest symbol","RELIANCE")
    period=st.selectbox("History",["1y","2y","5y"],index=1)
    if st.button("Run Backtest"):
        df=cached_history(ticker.upper().replace(".NS","")+".NS",period,"1d")
        metrics,trades=backtest_vwap_momentum(df,capital,risk_pct,SETTINGS.min_rr)
        if "error" in metrics: st.error(metrics["error"])
        else:
            cols=st.columns(6)
            cols[0].metric("Trades",metrics["trades"]); cols[1].metric("Win Rate",f"{metrics['win_rate']}%")
            cols[2].metric("Profit Factor",metrics["profit_factor"]); cols[3].metric("Max DD",f"{metrics['max_drawdown']}%")
            cols[4].metric("Total P&L",money(metrics["total_pnl"])); cols[5].metric("Final Capital",money(metrics["final_capital"]))
            if not trades.empty:
                st.line_chart((trades["pnl"].cumsum()+capital))
                st.dataframe(trades,use_container_width=True,hide_index=True)

elif page=="Signal History":
    st.subheader("📜 Signal History")
    df=read_signals(500)
    st.dataframe(df,use_container_width=True,hide_index=True)
    if not df.empty:
        st.download_button("Download CSV",df.to_csv(index=False).encode(),"signal_history.csv","text/csv")

elif page=="Paper Risk":
    st.subheader("💰 Paper Position Sizing & Risk")
    entry=st.number_input("Entry",min_value=0.01,value=100.0)
    sl=st.number_input("Stop Loss",min_value=0.01,value=98.0)
    risk_amount=capital*risk_pct/100
    per_share=abs(entry-sl)
    qty=int(risk_amount/per_share) if per_share else 0
    pos=qty*entry
    c1,c2,c3=st.columns(3)
    c1.metric("Risk Amount",money(risk_amount))
    c2.metric("Quantity",f"{qty:,}")
    c3.metric("Position Value",money(pos))
    st.info("Paper mode only. No broker order execution is connected.")
