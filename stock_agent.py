"""Free-data stock research CLI. No paid AI API is required."""
import sys
from data_engine import fetch_multi_timeframe
from quant_engine import market_regime, score_symbol

def analyze(ticker):
    frames=fetch_multi_timeframe(ticker)
    d1=frames["1d"]
    if d1.empty:
        return {"error":"No free market data returned."}
    regime=market_regime(d1)
    result=score_symbol(frames["15m"],regime)
    if result is None:
        return {"error":"Insufficient intraday data."}
    result["symbol"]=ticker.upper().replace(".NS","")
    result["regime"]=regime["regime"]
    return result

if __name__=="__main__":
    ticker=sys.argv[1] if len(sys.argv)>1 else input("Enter NSE ticker: ").strip()
    print(analyze(ticker))
