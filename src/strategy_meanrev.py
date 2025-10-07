from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
from .config import Config
from .indicators import ma, rolling_std, zscore_last, pct_change, last_valid

@dataclass
class CoinRow:
    id: str
    symbol: str
    name: str
    price: float
    volume24: float
    ma3: Optional[float]
    ma7: Optional[float]
    std7: Optional[float]
    z7: Optional[float]
    d3: Optional[float]
    d7: Optional[float]

@dataclass
class SignalRow(CoinRow):
    arrow: str  # ↑ ↓ ↗ ↘
    verdict: str  # 🟢 / 🟡 / 🟠 / 🔴 (text)
    # for buys only
    entry: Optional[float] = None
    entry_better: Optional[float] = None
    sl: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    split_hint: Optional[bool] = None

def arrow_from_ma(ma3: Optional[float], ma7: Optional[float]) -> str:
    if ma3 is None or ma7 is None:
        return "·"
    if abs(ma3 - ma7) < 1e-9:
        return "·"
    return "↑" if ma3 > ma7 else "↓"

def soften_arrow(a: str, z: Optional[float]) -> str:
    # convert strong arrows to diagonal if |z| is small
    if z is None:
        return a
    if abs(z) < 0.6:
        return "↗" if a == "↑" else ("↘" if a == "↓" else a)
    return a

def verdict_from(z: Optional[float], a: str, side: str) -> str:
    if z is None:
        return "🟡 Nenoteikts"
    if side == "BUY":
        if z <= -1.5:
            return "🟢 Vērts apsvērt — dziļš atvilkums"
        if z <= -1.2:
            return "🟢 Vērts apsvērt"
        return "🟡 Vēl jāgaida"
    else:
        if z >= 1.6:
            return "🔴 Pārvērtēts — korekcijas risks"
        if z >= 1.2:
            return "🟠 Uzmanīgi — var sekot pullback"
        return "🟡 Nedaudz pārvērtēts"

def compute_levels(price: float, ma7: Optional[float], std7: Optional[float]):
    if ma7 is None or std7 is None:
        return None
    e = price
    e_b = min(price, ma7 - 0.25 * std7)
    sl = price - 1.25 * std7
    tp1 = ma7
    tp2 = ma7 + 0.5 * std7
    split = price < (ma7 - 1.5 * std7)
    return e, e_b, sl, tp1, tp2, split

def build_signals(cfg: Config, market_rows: List[dict], prices: Dict[str, List[float]]):
    rows: List[CoinRow] = []
    for m in market_rows:
        pid = m["id"]
        series = prices.get(pid)
        if not series or len(series) < max(7, cfg.ZSCORE_WINDOW) or m.get("current_price") is None:
            continue
        ma3 = last_valid(ma(series, cfg.MA_SHORT))
        ma7 = last_valid(ma(series, cfg.MA_BASE))
        std7 = last_valid(rolling_std(series, cfg.ZSCORE_WINDOW))
        z7 = zscore_last(series, cfg.ZSCORE_WINDOW)
        d3 = pct_change(series, 3)
        d7 = pct_change(series, 7)
        rows.append(CoinRow(
            id=pid,
            symbol=(m.get("symbol") or "").upper(),
            name=m.get("name") or pid,
            price=float(m["current_price"]),
            volume24=float(m.get("total_volume") or 0.0),
            ma3=ma3, ma7=ma7, std7=std7, z7=z7, d3=d3, d7=d7
        ))

    buys: List[SignalRow] = []
    sells: List[SignalRow] = []

    for r in rows:
        a = soften_arrow(arrow_from_ma(r.ma3, r.ma7), r.z7)
        if r.z7 is None:
            continue
        if r.z7 <= -cfg.ZSCORE_THRESHOLD:
            verdict = verdict_from(r.z7, a, "BUY")
            lvls = compute_levels(r.price, r.ma7, r.std7)
            e=e_b=sl=tp1=tp2=None; split=False
            if lvls:
                e, e_b, sl, tp1, tp2, split = lvls
            buys.append(SignalRow(**r.__dict__, arrow=a, verdict=verdict,
                                  entry=e, entry_better=e_b, sl=sl, tp1=tp1, tp2=tp2, split_hint=split))
        elif r.z7 >= cfg.ZSCORE_THRESHOLD:
            verdict = verdict_from(r.z7, a, "SELL")
            sells.append(SignalRow(**r.__dict__, arrow=a, verdict=verdict))

    # sortings
    buys.sort(key=lambda x: x.z7 if x.z7 is not None else 0.0)  # most negative first
    sells.sort(key=lambda x: x.z7 if x.z7 is not None else 0.0, reverse=True)

    return buys[:cfg.BUY_TOP_N], sells[:cfg.SELL_TOP_N]
