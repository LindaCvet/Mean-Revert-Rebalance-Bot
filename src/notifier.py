from __future__ import annotations
from typing import Iterable
import httpx
import time

def send_telegram_message(bot_token: str, chat_ids: Iterable[str], text: str, disable_web_page_preview: bool = True):
    if not bot_token or not chat_ids:
        return False, "No Telegram token/chat_id"
    api = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    ok_all = True
    err_any = None
    with httpx.Client(timeout=30) as client:
        for cid in chat_ids:
            try:
                resp = client.post(api, data={
                    "chat_id": cid,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": "true" if disable_web_page_preview else "false"
                })
                if resp.status_code != 200:
                    ok_all = False
                    err_any = f"{resp.status_code} {resp.text[:200]}"
                time.sleep(0.5)  # gentle throttle
            except Exception as e:
                ok_all = False
                err_any = str(e)
    return ok_all, err_any
