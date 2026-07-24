from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    bot_token: str
    check_interval_minutes: int
    db_path: str
    request_timeout: float
    max_ads_per_check: int
    max_pages: int
    webhook_url: Optional[str]
    webhook_secret: Optional[str]
    port: int


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN не заданий. Додайте його у файл .env")

    return Config(
        bot_token=token,
        check_interval_minutes=int(os.getenv("CHECK_INTERVAL_MINUTES", "10")),
        db_path=os.getenv("DB_PATH", str(BASE_DIR / "data" / "olx_bot.db")),
        request_timeout=float(os.getenv("REQUEST_TIMEOUT", "15")),
        max_ads_per_check=int(os.getenv("MAX_ADS_PER_CHECK", "10")),
        max_pages=int(os.getenv("MAX_PAGES", "5")),
        # Публічна адреса сервісу для режиму webhook (Render підставляє
        # RENDER_EXTERNAL_URL автоматично, для локального polling не потрібно).
        webhook_url=os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL"),
        webhook_secret=os.getenv("WEBHOOK_SECRET"),
        port=int(os.getenv("PORT", "8080")),
    )
