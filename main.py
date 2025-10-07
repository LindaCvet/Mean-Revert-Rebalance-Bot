from __future__ import annotations
import sys
from typing import List
from src.config import Config
from src.data_sources import get_top_market, build_price_panel
from src.strategy_meanrev import build_signals
from src.formatter import build_message_lv
from src.notifier import send_telegram_message

def main():
    cfg = Config()

    # 1) Fetch universe
    try:
        market = get_top_market(cfg)
        if not market:
            raise RuntimeError("Empty market universe after filters.")
    except Exception as e:
        text = f"Mean-Revert: Skipped run (CoinGecko kļūda): {e}"
        send_telegram_message(cfg.TG_BOT_TOKEN, cfg.TG_CHAT_IDS, text)
        print(text, file=sys.stderr)
        return

    # 2) Fetch daily prices
    try:
        panel = build_price_panel(cfg, market)
    except Exception as e:
        text = f"Mean-Revert: Skipped run (CG cenas nav pieejamas): {e}"
        send_telegram_message(cfg.TG_BOT_TOKEN, cfg.TG_CHAT_IDS, text)
        print(text, file=sys.stderr)
        return

    # 3) Compute signals
    buys, sells = build_signals(cfg, market, panel)

    # 4) Build message (LV)
    msg = build_message_lv(cfg, buys, sells)

    # 5) Notify
    ok, err = send_telegram_message(cfg.TG_BOT_TOKEN, cfg.TG_CHAT_IDS, msg)
    if not ok:
        print(f"Telegram send error: {err}", file=sys.stderr)
    else:
        print("OK")

if __name__ == "__main__":
    main()
