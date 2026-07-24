from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from .config import Config
from .db.database import Database
from .olx.parser import fetch_ads

logger = logging.getLogger(__name__)


async def check_subscriptions(bot: Bot, db: Database, config: Config) -> None:
    """Перевіряє всі підписки всіх користувачів і надсилає нові оголошення."""
    subscriptions = await db.all_subscriptions()

    for row in subscriptions:
        try:
            ads = await fetch_ads(row["url"], timeout=config.request_timeout)
        except Exception as exc:
            logger.warning("Не вдалося завантажити %s: %s", row["url"], exc)
            continue

        seen = await db.get_seen_ad_ids(row["id"])
        new_ads = [ad for ad in ads if ad.ad_id not in seen][: config.max_ads_per_check]

        for ad in new_ads:
            try:
                await bot.send_message(
                    row["chat_id"],
                    f"🆕 [{row['label']}] {ad.title}\n{ad.price}\n{ad.location_date}\n{ad.url}",
                )
                await asyncio.sleep(0.5)
            except Exception as exc:
                logger.warning("Не вдалося надіслати повідомлення %s: %s", row["chat_id"], exc)

        await db.mark_ads_seen(row["id"], [ad.ad_id for ad in ads])
