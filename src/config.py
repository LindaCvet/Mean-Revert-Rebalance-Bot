from __future__ import annotations
import os
from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class Config:
    # Universe
    UNIVERSE: str = os.getenv("UNIVERSE", "TOP100")  # TOP50 | TOP100 | MANUAL
    WATCHLIST: List[str] = tuple(
        sym.strip().lower() for sym in os.getenv("WATCHLIST", "").split(",") if sym.strip()
    )

    # Filters
    MIN_VOLUME_USD_24H: float = float(os.getenv("MIN_VOLUME_USD_24H", "20000000"))
    MIN_PRICE_USD: float = float(os.getenv("MIN_PRICE_USD", "0.05"))
    EXCLUDE_STABLES: bool = os.getenv("EXCLUDE_STABLES", "true").lower() == "true"

    # Indicators
    MA_BASE: int = int(os.getenv("MA_BASE", "7"))
    MA_SHORT: int = int(os.getenv("MA_SHORT", "3"))
    ZSCORE_WINDOW: int = int(os.getenv("ZSCORE_WINDOW", "7"))
    ZSCORE_THRESHOLD: float = float(os.getenv("ZSCORE_THRESHOLD", "1.2"))

    # Candidates
    BUY_TOP_N: int = int(os.getenv("BUY_TOP_N", "5"))
    SELL_TOP_N: int = int(os.getenv("SELL_TOP_N", "5"))

    # Messaging
    LANG: str = os.getenv("LANG", "LV")
    TG_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TG_CHAT_IDS: List[str] = tuple(
        x.strip() for x in os.getenv("TELEGRAM_CHAT_ID", "").split(",") if x.strip()
    )

    # Data
    COINGECKO_API_KEY: str | None = os.getenv("COINGECKO_API_KEY") or None
    CG_DAYS: int = int(os.getenv("CG_DAYS", "30"))
    CG_TIMEOUT: float = float(os.getenv("CG_TIMEOUT", "30"))

    # Robust rate-limit controls (NEW)
    RATE_LIMIT_SLEEP: float = float(os.getenv("RATE_LIMIT_SLEEP", "1.2"))  # pause starp zvaniem
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "6"))                  # max atkārtojumi uz 429/5xx
    RETRY_BACKOFF_MIN: float = float(os.getenv("RETRY_BACKOFF_MIN", "1.0"))
    RETRY_BACKOFF_MAX: float = float(os.getenv("RETRY_BACKOFF_MAX", "25.0"))

    # Misc
    TZ_NAME: str = os.getenv("TZ_NAME", "Europe/Riga")

STABLES = {
    "tether", "usd-coin", "binance-usd", "dai", "true-usd", "usdd", "frax",
    "paxos-standard", "first-digital-usd", "gemini-dollar", "paypal-usd",
    "lusd", "usdx", "musd", "susd", "fei-usd", "liquity-usd"
}
