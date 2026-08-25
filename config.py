import os
import streamlit as st
from dataclasses import dataclass

def get_secret(key, default=""):
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)

@dataclass(frozen=True)
class Settings:
    app_title: str = "INSTITUTIONAL QUANT TERMINAL V2"
    refresh_seconds: int = 30
    min_signal_score: int = 60  # अलर्ट टेस्ट करण्यासाठी लिमिट ६० केले आहे
    min_rr: float = 1.5         # अलर्ट टेस्ट करण्यासाठी R:R १.५ केले आहे
    default_capital: float = 1_000_000.0
    default_risk_pct: float = 0.5

    # 🔽 खालील दोन ओळींमध्ये तुमचे Telegram डिटेल्स टाका 🔽
    telegram_token_manual: str = "8928624733:AAFGEGLtrB_BqXMUQd8sJbY7dcT44L0Nk-g"
    telegram_chat_id_manual: str = "8419107381"

    @property
    def telegram_token(self):
        val = get_secret("8928624733:AAFGEGLtrB_BqXMUQd8sJbY7dcT44L0Nk-g")
        return val if val else self.telegram_token_manual

    @property
    def telegram_chat_id(self):
        val = get_secret("8419107381")
        return val if val else self.telegram_chat_id_manual

SETTINGS = Settings()

INDICES = {
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK",
    "SENSEX": "^BSESN",
    "INDIA VIX": "^INDIAVIX",
}

SECTOR_INDICES = {
    "BANKING": "^NSEBANK",
    "IT": "^CNXIT",
    "AUTO": "^CNXAUTO",
    "PHARMA": "^CNXPHARMA",
    "METAL": "^CNXMETAL",
    "FMCG": "^CNXFMCG",
    "ENERGY": "^CNXENERGY",
    "REALTY": "^CNXREALTY",
    "PSU BANK": "^CNXPSUBANK",
    "FINANCIAL": "^CNXFIN",
}

# Updated Clean Watchlist (Without TATAMOTORS.NS)
STOCK_SYMBOLS = [
    "^NSEI",         # NIFTY 50
    "^NSEBANK",      # BANK NIFTY
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "BHARTIARTL.NS",
    "SBIN.NS",
    "LTIM.NS"
]