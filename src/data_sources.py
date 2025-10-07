from __future__ import annotations
import time
import random
from typing import Dict, List, Tuple, Optional
import httpx
from .config import Config, STABLES

CG_BASE = "https://api.coingecko.com/api/v3"


def _headers(cfg: Config) -> Dict[str, str]:
    h = {"Accept": "application/json", "User-Agent": "meanrev-bot/1.1"}
    if cfg.COINGECKO_API_KEY:
        h["x-cg-pro-api-key"] = cfg.COINGECKO_API_KEY
    return h


def _respect_retry_after(resp: httpx.Response) -> Optional[float]:
    """If API returns Retry-After, parse it (seconds)."""
    ra = resp.headers.get("Retry-After")
    if not ra:
        return None
    try:
        return float(ra)
    except Exception:
        return None


def _sleep_with_jitter(base_seconds: float):
    # mazs jitter (±20%), lai izkliedētu viļņus
    jitter = base_seconds * (0.8 + 0.4 * random.random())
    time.sleep(jitter)


def _get_json_with_retry(cfg: Config, url: str, params: Dict) -> dict:
    """
    Robusts GET ar:
      - 429/5xx atkārtojumiem līdz cfg.MAX_RETRIES
      - Retry-After respect
      - eksponenciālu backoff ar griestiem
    """
    headers = _headers(cfg)
    backoff = cfg.RETRY_BACKOFF_MIN

    last_err = None
    for attempt in range(1, cfg.MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=cfg.CG_TIMEOUT, headers=headers) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    return resp.json()

                # Rate limit vai server error
                if resp.status_code in (429, 500, 502, 503, 504):
                    wait_hdr = _respect_retry_after(resp)
                    wait_sec = wait_hdr if wait_hdr is not None else backoff
                    # clamp
                    wait_sec = min(max(wait_sec, cfg.RETRY_BACKOFF_MIN), cfg.RETRY_BACKOFF_MAX)
                    _sleep_with_jitter(wait_sec)
                    backoff = min(backoff * 1.7, cfg.RETRY_BACKOFF_MAX)
                    last_err = f"{resp.status_code} {resp.text[:160]}"
                    continue

                # citi HTTP status — nelabojama kļūda
                resp.raise_for_status()

        except httpx.HTTPError as e:
            last_err = str(e)
            # eksponenciāls backoff arī uz tīkla kļūdām
            _sleep_with_jitter(backoff)
            backoff = min(backoff * 1.7, cfg.RETRY_BACKOFF_MAX)

    raise RuntimeError(f"CG request failed after {cfg.MAX_RETRIES} retries: {last_err}")


def get_top_market(cfg: Config) -> List[dict]:
    """Top coins by market cap with 24h volume and current price."""
    url = f"{CG_BASE}/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 250,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "7d,30d",
    }
    data = _get_json_with_retry(cfg, url, params)

    # Universe slice
    if cfg.UNIVERSE == "TOP50":
        data = data[:50]
    elif cfg.UNIVERSE == "TOP100":
        data = data[:100]
    elif cfg.UNIVERSE == "MANUAL":
        wl = set(cfg.WATCHLIST)
        data = [x for x in data if x.get("id") in wl]
    else:
        data = data[:100]

    # Exclude stables
    if cfg.EXCLUDE_STABLES:
        data = [x for x in data if (x.get("id") or "") not in STABLES]

    # Basic liquidity/price filters
    out = []
    for x in data:
        vol = float(x.get("total_volume") or 0.0)
        px = float(x.get("current_price") or 0.0)
        if vol >= cfg.MIN_VOLUME_USD_24H and px >= cfg.MIN_PRICE_USD:
            out.append(x)
    return out


def get_market_chart_daily(cfg: Config, coin_id: str, days: int) -> List[Tuple[int, float]]:
    """Return list of (timestamp_ms, price) daily sampled."""
    url = f"{CG_BASE}/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days, "interval": "daily"}
    js = _get_json_with_retry(cfg, url, params)
    prices = js.get("prices", [])  # [[ts, price], ...]
    if not prices:
        # dažkārt CG atgriež tukšu masīvu — mēģinam vienu “vēsāku” piegājienu
        _sleep_with_jitter(cfg.RATE_LIMIT_SLEEP + 0.6)
        js = _get_json_with_retry(cfg, url, params)
        prices = js.get("prices", [])
    return [(int(ts), float(p)) for ts, p in prices]


def build_price_panel(cfg: Config, coins: List[dict]) -> Dict[str, List[float]]:
    """
    For each coin id, fetch daily close array (in USD). Returns dict: id -> closes (ascending by time).
    Ar saudzīgu throttlingu un retry.
    """
    out: Dict[str, List[float]] = {}
    for i, c in enumerate(coins):
        cid = c["id"]
        series = get_market_chart_daily(cfg, cid, cfg.CG_DAYS)
        closes = [p for _, p in series]
        # Der tikai tad, ja ir pietiekami datu (>= 8 dienām drošībai)
        if len(closes) >= max(8, cfg.ZSCORE_WINDOW + 1):
            out[cid] = closes[-max(14, cfg.CG_DAYS):]
        # starp zvaniem — pauze ar jitter
        _sleep_with_jitter(cfg.RATE_LIMIT_SLEEP)
    return out
