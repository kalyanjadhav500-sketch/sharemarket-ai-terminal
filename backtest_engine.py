from data_engine import fetch_stock_data

def run_backtest(ticker="^NSEI", period="1mo"):
    df = fetch_stock_data(ticker, period=period, interval="15m")
    if df is None or df.empty:
        print("No data retrieved for backtesting.")
        return

    trades = []
    in_trade = False
    entry_price = 0.0

    for i in range(21, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        if not in_trade:
            # Entry condition: EMA 9 crosses above EMA 21 and RSI > 53
            if (prev['ema_9'] <= prev['ema_21']) and (row['ema_9'] > row['ema_21']) and (row['rsi'] > 53):
                in_trade = True
                entry_price = row['close']
        else:
            pnl_pct = ((row['close'] - entry_price) / entry_price) * 100
            # Exit condition: Target +1.5% or Stoploss -0.8%
            if pnl_pct >= 1.5 or pnl_pct <= -0.8:
                trades.append(pnl_pct)
                in_trade = False

    total_trades = len(trades)
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0.0
    profit_factor = round(sum(wins) / (abs(sum(losses)) + 1e-9), 2)

    print(f"\n📊 --- BACKTEST REPORT: {ticker} ---")
    print(f"Total Signals Evaluated: {total_trades}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Profit Factor: {profit_factor}")

if __name__ == "__main__":
    run_backtest("^NSEI")