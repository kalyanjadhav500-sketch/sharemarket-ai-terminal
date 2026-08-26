import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import yfinance as yf

def clean_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if s.startswith("^"):
        return s
    return s if s.endswith(".NS") else f"{s}.NS"

def fetch_stock_data(symbol: str, period="1mo", interval="15m", retries=2):
    symbol = clean_symbol(symbol)
    for attempt in range(retries + 1):
        try:
            df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False, actions=False)
            if df is not None and not df.empty:
                df = df.copy()
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                # कॉलमची नावे Lowercase मध्ये बदलणे (यामुळे KeyError येत नाही)
                df.columns = [str(c).lower() for c in df.columns]
                df.index = pd.to_datetime(df.index)
                return df.dropna(subset=["open", "high", "low", "close"])
        except Exception:
            if attempt < retries:
                time.sleep(0.7)
    return pd.DataFrame()

def fetch_history(symbol: str, period="1mo", interval="15m", retries=2):
    return fetch_stock_data(symbol, period=period, interval=interval, retries=retries)

def fetch_multi_timeframe(symbol: str):
    return {
        "5m": fetch_stock_data(symbol, "5d", "5m"),
        "15m": fetch_stock_data(symbol, "1mo", "15m"),
        "1h": fetch_stock_data(symbol, "3mo", "1h"),
        "1d": fetch_stock_data(symbol, "2y", "1d"),
    }

def fetch_many(symbols, period="1mo", interval="15m", workers=6):
    out = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        jobs = {ex.submit(fetch_stock_data, s, period, interval): s for s in symbols}
        for job in as_completed(jobs):
            s = jobs[job]
            try:
                out[s] = job.result()
            except Exception:
                out[s] = pd.DataFrame()
    return out

def market_status(now=None):
    ts = pd.Timestamp.now(tz="Asia/Kolkata") if now is None else pd.Timestamp(now)
    if ts.weekday() >= 5:
        return "CLOSED"
    mins = ts.hour * 60 + ts.minute
    return "OPEN" if 9*60+15 <= mins <= 15*60+30 else "CLOSED"