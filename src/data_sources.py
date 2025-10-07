from __future__ import annotations
import time
from typing import Dict, List, Tuple
import httpx
from tenacity import retry, wait_exponential, stop_after_attempt
from .config import Config, STABLES

CG_BASE = "https://api.coingecko.com/api/v3"

def _headers(cfg: Config) -> Dict[str, str]:
    h = {"Accept": "application/json", "User-Agent": "meanrev-bot/1.0"}
    if cfg.COINGECKO_API_KEY:
        h["x-cg-pro-api-key"] = cfg.COINGECKO_API_KEY
    return h

@retry(wait=wait_exponential(multiplier=1, min=2, max=20), stop=stop_after_attempt(4))
def get_top_market(cfg: Config) -> List[dict]:
    """Top coins by market cap with 24h volume and current price."""
    per_page = 250
    url = f"{CG_BASE}/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "7d,30d",
    }
    with httpx.Client(timeout=cfg.CG_TIMEOUT, headers=_headers(cfg)) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    # Filter top-50 / top-100
    if cfg.UNIVERSE == "TOP50":
        data = data[:50]
    elif cfg.UNIVERSE == "TOP100":
        data = data[:100]
    elif cfg.UNIVERSE == "MANUAL":
        wl = set(cfg.WATCHLIST)
        data = [x for x in data if x["id"] in wl]
    else:
        data = data[:100]

    # Exclude stables if needed
    if cfg.EXCLUDE_STABLES:
        data = [x for x in data if x.get("id") not in STABLES]

    # Basic filters
    data = [
        x for x in data
        if (x.get("total_volume") or 0) >= cfg.MIN_VOLUME_USD_24H and (x.get("current_price") or 0) >= cfg.MIN_PRICE_USD
    ]
    return data

@retry(wait=wait_exponential(multiplier=1, min=2, max=20), stop=stop_after_attempt(4))
def get_market_chart_daily(cfg: Config, coin_id: str, days: int) -> List[Tuple[int, float]]:
    """Return list of (timestamp_ms, price) daily sampled."""
    url = f"{CG_BASE}/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days, "interval": "daily"}
    with httpx.Client(timeout=cfg.CG_TIMEOUT, headers=_headers(cfg)) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        js = r.json()
    prices = js.get("prices", [])  # [[ts, price], ...]
    return [(int(ts), float(p)) for ts, p in prices]

def build_price_panel(cfg: Config, coins: List[dict]) -> Dict[str, List[float]]:
    """
    For each coin id, fetch daily close array (in USD). Returns dict: id -> closes (ascending by time).
    Throttles lightly to respect CG free limits.
    """
    out: Dict[str, List[float]] = {}
    for i, c in enumerate(coins):
        cid = c["id"]
        series = get_market_chart_daily(cfg, cid, cfg.CG_DAYS)
        closes = [p for _, p in series]
        # keep only last 14-30, enough for MA7/z7
        out[cid] = closes[-max(14, cfg.CG_DAYS):]
        # small pause to be gentle
        time.sleep(0.4)
    return out
