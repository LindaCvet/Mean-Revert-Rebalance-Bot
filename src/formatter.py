from __future__ import annotations
from datetime import datetime
from typing import List
from dateutil import tz
from .config import Config
from .strategy_meanrev import SignalRow

def fmt_pct(x):
    return "—" if x is None else f"{x:+.1f} %"

def fmt_z(z):
    return "—" if z is None else f"{z:+.2f}"

def fmt_price(value: float) -> str:
    if value is None:
        return "—"
    return f"${value:.4f}" if value < 1 else f"${value:.2f}"

def header(cfg: Config) -> str:
    now = datetime.utcnow().replace(tzinfo=tz.UTC).astimezone(tz.gettz(cfg.TZ_NAME))
    return f"## 🧠 Mean-Revert Rebalance — Daily Summary\n🕓 {now:%Y-%m-%d} | ⏰ {now:%H:%M} {cfg.TZ_NAME.split('/')[-1]}\n\n---"

def section_table(title: str, rows: List[SignalRow], side: str) -> str:
    if not rows:
        return f"\n### {title}\nNav kandidātu pēc pašreizējiem filtri/sliekšņiem.\n"
    lines = [
        f"### {title}",
        "| Coin | Z | 3d % | 7d % | Signāls |",
        "|:-----|:--:|:----:|:----:|:--------|",
    ]
    for r in rows:
        sign = f"{r.verdict}"
        ztxt = f"{fmt_z(r.z7)} {r.arrow}"
        lines.append(f"| **{r.symbol}** | {ztxt} | {fmt_pct(r.d3)} | {fmt_pct(r.d7)} | {sign} |")
    return "\n".join(lines)

def buy_levels(rows: List[SignalRow]) -> str:
    keep = [r for r in rows if r.entry is not None]
    if not keep:
        return ""
    lines = ["\n**🎯 Tirdzniecības līmeņi (tikai Buy kandidātiem)**"]
    lines.append("> Skaitļi no CG dienas datiem; cenas < $1 → 4 dec., citādi → 2 dec.")
    for r in keep:
        extra = f" *(Eₗ: {fmt_price(r.entry_better)})*" if r.entry_better is not None else ""
        split = " · _Ieteikums: sadalīt pirkumu 2–3 daļās_" if r.split_hint else ""
        lines.append(
            f"- **{r.symbol}** — `E` {fmt_price(r.entry)}{extra} · "
            f"`SL` {fmt_price(r.sl)} · `TP1` {fmt_price(r.tp1)} · `TP2` {fmt_price(r.tp2)}{split}"
        )
    return "\n".join(lines)

def summary_line(buys: List[SignalRow], sells: List[SignalRow]) -> str:
    b = ", ".join([r.symbol for r in buys]) or "—"
    s = ", ".join([r.symbol for r in sells]) or "—"
    return f"\n📊 **Kopsavilkums:**\n👉 **Šodienas skatījums:** *Buy zonas:* {b}; *Sell zonas:* {s}.\n" \
           f"*Mean-revert skatījums — ne finanšu konsultācija. Dati: CoinGecko; Z = 7d logs; MA(3/7).*"

def build_message_lv(cfg: Config, buys: List[SignalRow], sells: List[SignalRow]) -> str:
    parts = [
        header(cfg),
        section_table("🟩 Buy candidates *(pārpārdotie, iespējama atgriešanās pie vidējās)*", buys, "BUY"),
        section_table("🟥 Sell / Trim candidates *(pārpirk tieksme, iespējams korekcijas risks)*", sells, "SELL"),
        buy_levels(buys),
        summary_line(buys, sells)
    ]
    return "\n\n".join(parts)
