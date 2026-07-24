from __future__ import annotations

import logging
from dataclasses import replace

from aiogram import Bot

from .config import Config
from .olx.models import Ad
from .olx.parser import fetch_ad_description

logger = logging.getLogger(__name__)

MAX_CAPTION_LENGTH = 1024


def _build_caption(label: str, ad: Ad) -> str:
    header = f"🆕 [{label}] {ad.title}"
    footer_parts = [ad.price]
    if ad.location_date:
        footer_parts.append(ad.location_date)
    footer_parts.append(ad.url)
    footer = "\n".join(footer_parts)

    description = (ad.description or "").strip()
    # Опис обрізаємо так, щоб заголовок, ціна й посилання завжди лишались цілими.
    available = MAX_CAPTION_LENGTH - len(header) - len(footer) - 4
    if description and available > 0:
        if len(description) > available:
            description = description[: available - 1].rstrip() + "…"
        return f"{header}\n\n{description}\n\n{footer}"

    return f"{header}\n\n{footer}"


async def send_ad(bot: Bot, chat_id: int, label: str, ad: Ad, config: Config) -> None:
    """Надсилає користувачу картку оголошення: фото (якщо є), ціну, опис і посилання."""
    try:
        description = await fetch_ad_description(ad.url, timeout=config.request_timeout)
    except Exception as exc:
        logger.warning("Не вдалося отримати опис %s: %s", ad.url, exc)
        description = None

    if description:
        ad = replace(ad, description=description)

    caption = _build_caption(label, ad)

    if ad.image_url:
        try:
            await bot.send_photo(chat_id, photo=ad.image_url, caption=caption)
            return
        except Exception as exc:
            logger.warning("Не вдалося надіслати фото %s: %s", ad.image_url, exc)

    await bot.send_message(chat_id, caption)
