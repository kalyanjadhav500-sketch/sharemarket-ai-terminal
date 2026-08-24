import math
import numpy as np
import pandas as pd

def rsi(s, period=14):
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50)

def atr(df, period=14):
    prev = df["Close"].shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - prev).abs(),
        (df["Low"] - prev).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False, min_periods=period).mean()

def adx(df, period=14):
    up = df["High"].diff()
    down = -df["Low"].diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0), index=df.index)
    a = atr(df, period).replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1/period, adjust=False).mean() / a
    minus_di = 100 * minus_dm.ewm(alpha=1/period, adjust=False).mean() / a
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    return dx.ewm(alpha=1/period, adjust=False).mean().fillna(0)

def macd(s):
    e12 = s.ewm(span=12, adjust=False).mean()
    e26 = s.ewm(span=26, adjust=False).mean()
    line = e12 - e26
    signal = line.ewm(span=9, adjust=False).mean()
    return line, signal, line-signal

def add_indicators(df):
    if df.empty:
        return df
    x = df.copy()
    tp = (x["High"] + x["Low"] + x["Close"]) / 3
    vol = x["Volume"].fillna(0)
    # Session VWAP is reset by trading date.
    dates = x.index.tz_convert("Asia/Kolkata").date if getattr(x.index, "tz", None) else x.index.date
    x["_date"] = dates
    pv = tp * vol
    x["VWAP"] = pv.groupby(x["_date"]).cumsum() / vol.groupby(x["_date"]).cumsum().replace(0, np.nan)
    x["VWAP"] = x["VWAP"].fillna(x["Close"])
    for n in (9, 21, 50, 100, 200):
        x[f"EMA_{n}"] = x["Close"].ewm(span=n, adjust=False).mean()
    x["SMA_20"] = x["Close"].rolling(20).mean()
    x["SMA_50"] = x["Close"].rolling(50).mean()
    x["SMA_200"] = x["Close"].rolling(200).mean()
    x["RSI"] = rsi(x["Close"])
    x["ATR"] = atr(x)
    x["ADX"] = adx(x)
    x["BB_MID"] = x["Close"].rolling(20).mean()
    std = x["Close"].rolling(20).std()
    x["BB_UPPER"] = x["BB_MID"] + 2*std
    x["BB_LOWER"] = x["BB_MID"] - 2*std
    x["MACD"], x["MACD_SIGNAL"], x["MACD_HIST"] = macd(x["Close"])
    x["VOL_AVG_20"] = x["Volume"].rolling(20).mean()
    x["REL_VOLUME"] = x["Volume"] / x["VOL_AVG_20"].replace(0, np.nan)
    x["ROC_10"] = x["Close"].pct_change(10) * 100
    x["DAY_HIGH"] = x["High"].rolling(78, min_periods=1).max()
    x["DAY_LOW"] = x["Low"].rolling(78, min_periods=1).min()
    x["SWING_HIGH_20"] = x["High"].rolling(20).max().shift(1)
    x["SWING_LOW_20"] = x["Low"].rolling(20).min().shift(1)
    return x.drop(columns=["_date"], errors="ignore")

def timeframe_state(df):
    if df.empty or len(df) < 30:
        return {"state":"DATA UNAVAILABLE","score":50}
    x = add_indicators(df)
    l = x.iloc[-1]
    bull = 0
    bear = 0
    bull += 25 if l["Close"] > l["EMA_21"] else 0
    bear += 25 if l["Close"] < l["EMA_21"] else 0
    bull += 20 if l["EMA_9"] > l["EMA_21"] else 0
    bear += 20 if l["EMA_9"] < l["EMA_21"] else 0
    bull += 20 if l["Close"] > l["VWAP"] else 0
    bear += 20 if l["Close"] < l["VWAP"] else 0
    bull += 20 if l["RSI"] > 55 else 0
    bear += 20 if l["RSI"] < 45 else 0
    if bull >= 70 and bull > bear:
        state = "BULLISH"
    elif bear >= 70 and bear > bull:
        state = "BEARISH"
    else:
        state = "NEUTRAL"
    return {"state":state, "bull":bull, "bear":bear, "score":max(bull,bear)}

def market_regime(index_df):
    if index_df.empty or len(index_df) < 50:
        return {"regime":"DATA UNAVAILABLE","score":50,"bull":50,"bear":50}
    x = add_indicators(index_df)
    l = x.iloc[-1]
    bull = 0
    bear = 0
    bull += 30 if l["Close"] > l["EMA_50"] else 0
    bear += 30 if l["Close"] < l["EMA_50"] else 0
    bull += 25 if l["EMA_21"] > l["EMA_50"] else 0
    bear += 25 if l["EMA_21"] < l["EMA_50"] else 0
    bull += 20 if l["ADX"] >= 20 and l["ROC_10"] > 0 else 0
    bear += 20 if l["ADX"] >= 20 and l["ROC_10"] < 0 else 0
    bull += 25 if l["Close"] > l["VWAP"] else 0
    bear += 25 if l["Close"] < l["VWAP"] else 0
    if max(bull,bear) < 55:
        regime = "RANGE / UNCERTAIN"
    elif bull >= 70 and bull > bear:
        regime = "TRENDING BULL"
    elif bear >= 70 and bear > bull:
        regime = "TRENDING BEAR"
    elif l["ADX"] >= 25:
        regime = "HIGH-MOMENTUM"
    else:
        regime = "TRANSITION"
    return {"regime":regime, "score":max(bull,bear), "bull":bull, "bear":bear, "adx":float(l["ADX"])}

def sector_strength(sector_data):
    rows=[]
    for name, df in sector_data.items():
        if df.empty or len(df)<5:
            continue
        close=df["Close"].dropna()
        ret=float((close.iloc[-1]/close.iloc[0]-1)*100)
        rows.append({"sector":name,"return_pct":round(ret,2)})
    if not rows:
        return pd.DataFrame(columns=["sector","return_pct","rank_score"])
    out=pd.DataFrame(rows).sort_values("return_pct",ascending=False).reset_index(drop=True)
    ranks=len(out)-out.index
    out["rank_score"]=(ranks/ranks.max()*100).round(1)
    return out

def score_symbol(df, regime, sector_score=50):
    if df.empty or len(df)<40:
        return None
    x=add_indicators(df)
    l=x.iloc[-1]
    bull=0.0
    bear=0.0
    # 100-point bull/bear engines
    bull += 15 if regime["bull"] > regime["bear"] else 0
    bear += 15 if regime["bear"] > regime["bull"] else 0
    bull += 10 if l["Close"] > l["EMA_21"] else 0
    bear += 10 if l["Close"] < l["EMA_21"] else 0
    bull += 10 if l["Close"] > l["VWAP"] else 0
    bear += 10 if l["Close"] < l["VWAP"] else 0
    bull += 10 if 55 <= l["RSI"] <= 72 else 0
    bear += 10 if 28 <= l["RSI"] <= 45 else 0
    bull += 10 if l["MACD_HIST"] > 0 else 0
    bear += 10 if l["MACD_HIST"] < 0 else 0
    rv=float(l["REL_VOLUME"]) if pd.notna(l["REL_VOLUME"]) else 1.0
    bull += 10 if rv >= 1.5 and l["Close"] > l["Open"] else 0
    bear += 10 if rv >= 1.5 and l["Close"] < l["Open"] else 0
    bull += 10 if l["ADX"] >= 20 and l["EMA_9"] > l["EMA_21"] else 0
    bear += 10 if l["ADX"] >= 20 and l["EMA_9"] < l["EMA_21"] else 0
    bull += 5 if sector_score >= 60 else 0
    bear += 5 if sector_score <= 40 else 0
    bull += 10 if l["Close"] > l["SWING_HIGH_20"] else 0
    bear += 10 if l["Close"] < l["SWING_LOW_20"] else 0
    # Smart-money proxy is deliberately a proxy, not actual order-book flow.
    smart = min(100, 50 + (20 if rv >= 1.5 else 0) + (15 if l["Close"] > l["VWAP"] else -15) + (15 if l["Close"] > l["EMA_21"] else -15))
    atr_val=float(l["ATR"]) if pd.notna(l["ATR"]) and l["ATR"]>0 else float(l["Close"]*0.01)
    price=float(l["Close"])
    if bull > bear and bull >= 70:
        action="BUY"
        entry_low=price-0.20*atr_val
        entry_high=price+0.10*atr_val
        sl=price-1.0*atr_val
        tp1=price+1.5*atr_val
        tp2=price+2.5*atr_val
    elif bear > bull and bear >= 70:
        action="SELL"
        entry_low=price-0.10*atr_val
        entry_high=price+0.20*atr_val
        sl=price+1.0*atr_val
        tp1=price-1.5*atr_val
        tp2=price-2.5*atr_val
    else:
        action="NO TRADE"
        entry_low=entry_high=price
        sl=tp1=tp2=price
    risk=abs(price-sl)
    reward=abs(tp1-price)
    rr=(reward/risk) if risk else 0
    return {
        "price":round(price,2),"rsi":round(float(l["RSI"]),2),
        "adx":round(float(l["ADX"]),2),"vwap":round(float(l["VWAP"]),2),
        "rel_volume":round(rv,2),"atr":round(atr_val,2),
        "bull_score":round(min(100,bull),1),"bear_score":round(min(100,bear),1),
        "smart_money":round(smart,1),"action":action,
        "entry_low":round(entry_low,2),"entry_high":round(entry_high,2),
        "sl":round(sl,2),"tp1":round(tp1,2),"tp2":round(tp2,2),
        "rr":round(rr,2),"regime":regime["regime"]
    }

def build_scanner_row(symbol, df, regime, sector_score=50, sector="N/A"):
    s=score_symbol(df,regime,sector_score)
    if not s:
        return None
    s.update({"symbol":symbol.replace(".NS",""),"sector":sector})
    # Final conviction is transparent and capped; it is NOT an LLM confidence.
    dominant=max(s["bull_score"],s["bear_score"])
    s["confidence"]=round(dominant,1)
    return s

def analyze_index(symbol, df, name):
    if df.empty or len(df) < 30:
        return None
    x = add_indicators(df)
    l = x.iloc[-1]
    price = float(l["Close"])
    atr_val = float(l["ATR"]) if pd.notna(l["ATR"]) and l["ATR"] > 0 else price * 0.005
    
    bull = 0
    bear = 0
    bull += 30 if l["Close"] > l["EMA_21"] else 0
    bear += 30 if l["Close"] < l["EMA_21"] else 0
    bull += 25 if l["Close"] > l["VWAP"] else 0
    bear += 25 if l["Close"] < l["VWAP"] else 0
    bull += 25 if l["RSI"] > 55 else 0
    bear += 25 if l["RSI"] < 45 else 0
    bull += 20 if l["MACD_HIST"] > 0 else 0
    bear += 20 if l["MACD_HIST"] < 0 else 0

    if bull >= 60 and bull > bear:
        action = "BUY / CALL"
        entry = price
        sl = price - (1.0 * atr_val)
        tp = price + (1.8 * atr_val)
    elif bear >= 60 and bear > bull:
        action = "SELL / PUT"
        entry = price
        sl = price + (1.0 * atr_val)
        tp = price - (1.8 * atr_val)
    else:
        action = "NEUTRAL (RANGE)"
        entry = price
        sl = price - (0.8 * atr_val)
        tp = price + (0.8 * atr_val)

    return {
        "name": name,
        "symbol": symbol,
        "price": round(price, 2),
        "action": action,
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "rsi": round(float(l["RSI"]), 1),
        "bias": "BULLISH" if bull > bear else ("BEARISH" if bear > bull else "NEUTRAL")
    }
