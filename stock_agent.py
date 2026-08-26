import sys
from data_engine import fetch_stock_data
from quant_engine import analyze_institutional_matrix

def scan_stock(ticker):
    print(f"🔍 Running Quant AI Matrix Scan for: {ticker}...")
    df = fetch_stock_data(ticker, period="5d", interval="5m")
    if df is None:
        print(f"Could not retrieve data for ticker: {ticker}")
        return
    
    res = analyze_institutional_matrix(df)
    print("\n" + "="*40)
    print(f"  QUANT AI SCORECARD: {ticker}")
    print("="*40)
    print(f"Action Signal : {res['action']}")
    print(f"Confidence    : {res['confidence']}%")
    print(f"Entry Price   : ₹{res['entry_price']}")
    print(f"Target 1      : ₹{res['target1']}")
    print(f"Target 2      : ₹{res['target2']}")
    print(f"Stop Loss     : ₹{res['stop_loss']}")
    print(f"Risk/Reward   : {res['rr_ratio']}")
    print("\nConfluence Factors:")
    for reason in res['reasons']:
        print(f" • {reason}")

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "^NSEI"
    scan_stock(symbol)