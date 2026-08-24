# Institutional Quant Terminal V2

A free-data, local quantitative market-intelligence terminal for Indian equities.

## Important

This version intentionally removes the hardcoded OpenAI dependency and all paid-data requirements.

It uses free/public market-data access through `yfinance` plus local quantitative calculations. Free data can be delayed, incomplete, rate-limited, or unavailable. The application never fabricates unavailable values.

## Features

- Institutional-style Streamlit dashboard
- NIFTY 50 / BANK NIFTY / SENSEX / India VIX snapshot
- Market-regime engine
- Bull score and Bear score
- Multi-timeframe analysis
- RSI, EMA 9/21/50/100/200, SMA, VWAP, ATR, ADX, MACD, Bollinger Bands
- Relative-volume and smart-money proxy
- Sector rotation
- Market radar
- Professional interactive charts
- No-trade filtering
- Dynamic paper position sizing
- Local SQLite signal history
- Local backtesting
- Optional Telegram alerts
- No broker execution
- No paid service requirement

## Install

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## Secrets

Do not put secrets into source code.

Windows PowerShell:

```powershell
$env:TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
$env:TELEGRAM_CHAT_ID="YOUR_CHAT_ID"
```

For Streamlit deployment, use `.streamlit/secrets.toml` or your platform's secret manager and adapt the environment loading if required.

Telegram is optional. The terminal works without it.

## Run

```bash
streamlit run app.py
```

## Automatic Telegram scanner

```bash
python auto_telegram_scanner.py
```

The scanner is intentionally conservative and only sends when a setup clears the configured score and R:R thresholds.

## Security

The original project contained API credentials and a hardcoded password. Rotate any previously exposed credentials and do not reuse them.

## Data limitations

This is not a proprietary exchange feed. Free sources can be delayed or unavailable. Options/OI, FII/DII, delivery and true Level-2 order flow are not fabricated. Where a reliable free source is not available, the UI should show unavailable data rather than invent values.

## Backtesting

Backtesting is a research tool, not proof of future profitability. Always inspect assumptions, costs, slippage, data quality and survivorship bias before relying on results.
