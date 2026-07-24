from __future__ import annotations

import logging
from dataclasses import replace

from aiogram import Bot
from aiogram.types import InputMediaPhoto

from .config import Config
from .olx.models import Ad
from .olx.parser import fetch_ad_details

logger = logging.getLogger(__name__)

MAX_CAPTION_LENGTH = 1024
MAX_DESCRIPTION_LINES = 3
MAX_DESCRIPTION_CHARS = 168
MAX_ALBUM_PHOTOS = 6


def _short_description(description: str) -> str:
    lines = [line.strip() for line in description.splitlines() if line.strip()]
    short = "\n".join(lines[:MAX_DESCRIPTION_LINES])
    if len(short) > MAX_DESCRIPTION_CHARS:
        short = short[:MAX_DESCRIPTION_CHARS].rstrip() + "…"
    return short


def _build_caption(label: str, ad: Ad) -> str:
    header = f"🆕 [{label}] {ad.title}"
    footer_parts = [ad.price]
    if ad.location_date:
        footer_parts.append(ad.location_date)
    footer_parts.append(ad.url)
    footer = "\n".join(footer_parts)

    description = _short_description(ad.description or "")
    # Опис обрізаємо так, щоб заголовок, ціна й посилання завжди лишались цілими.
    available = MAX_CAPTION_LENGTH - len(header) - len(footer) - 4
    if description and available > 0:
        if len(description) > available:
            description = description[: available - 1].rstrip() + "…"
        return f"{header}\n\n{description}\n\n{footer}"

    return f"{header}\n\n{footer}"


def _ad_sort_key(ad: Ad) -> int:
    return int(ad.ad_id) if ad.ad_id.isdigit() else 0


def oldest_first(ads: list[Ad]) -> list[Ad]:
    """Сортує оголошення так, щоб найновіше (за id) було останнім у списку —
    тоді при послідовній відправці воно опиниться останнім і в чаті."""
    return sorted(ads, key=_ad_sort_key)


def select_new_ads(ads: list[Ad], seen_ids: set[str], limit: int) -> list[Ad]:
    """Відбирає оголошення, які ще не надсилались, і сортує від найстарішого
    до найновішого.

    Крім банальної перевірки "не в seen_ids", відкидає й ті, чий id не
    перевищує максимальний із уже надісланих. Це потрібно через рекламовані/
    просунуті оголошення на OLX: вони можуть з'явитись у видачі пізніше, ніж
    були створені, і без цієї перевірки "старе" оголошення могло б прийти
    вже після того, як надіслано щось новіше — порядок найновіше-останнім
    би зламався.
    """
    watermark = max((int(ad_id) for ad_id in seen_ids if ad_id.isdigit()), default=0)
    fresh = [
        ad
        for ad in ads
        if ad.ad_id not in seen_ids and (not ad.ad_id.isdigit() or int(ad.ad_id) > watermark)
    ]
    return oldest_first(fresh[:limit])


async def send_ad(bot: Bot, chat_id: int, label: str, ad: Ad, config: Config) -> None:
    """Надсилає користувачу картку оголошення: фото (альбом, якщо їх кілька), ціну, опис і посилання."""
    try:
        description, photos = await fetch_ad_details(ad.url, timeout=config.request_timeout)
    except Exception as exc:
        logger.warning("Не вдалося отримати деталі оголошення %s: %s", ad.url, exc)
        description, photos = None, []

    if description:
        ad = replace(ad, description=description)

    caption = _build_caption(label, ad)

    if not photos and ad.image_url:
        photos = [ad.image_url]
    photos = photos[:MAX_ALBUM_PHOTOS]

    if len(photos) >= 2:
        try:
            media = [
                InputMediaPhoto(media=url, caption=caption if i == 0 else None)
                for i, url in enumerate(photos)
            ]
            await bot.send_media_group(chat_id, media=media)
            return
        except Exception as exc:
            logger.warning("Не вдалося надіслати альбом %s: %s", ad.url, exc)

    if photos:
        try:
            await bot.send_photo(chat_id, photo=photos[0], caption=caption)
            return
        except Exception as exc:
            logger.warning("Не вдалося надіслати фото %s: %s", photos[0], exc)

    await bot.send_message(chat_id, caption)
