from __future__ import annotations

import asyncio
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..config import Config
from ..db.database import Database
from ..notify import send_ad
from ..olx.parser import fetch_ads

router = Router(name="subscriptions")
logger = logging.getLogger(__name__)

PREVIEW_COUNT = 3


def _is_olx_url(url: str) -> bool:
    return url.startswith("http") and "olx." in url


@router.message(Command("add"))
async def cmd_add(message: Message, db: Database, config: Config) -> None:
    args = (message.text or "").split(maxsplit=2)[1:]
    if len(args) < 2:
        await message.answer(
            "Формат: /add назва посилання_на_пошук_OLX\n"
            "Приклад: /add iphone https://www.olx.ua/uk/list/q-iphone-15/"
        )
        return

    label, url = args[0], args[1]
    if not _is_olx_url(url):
        await message.answer("Схоже, це не посилання на OLX. Перевірте URL і спробуйте ще раз.")
        return

    try:
        ads = await fetch_ads(url, timeout=config.request_timeout, max_pages=config.max_pages)
    except Exception:
        await message.answer("Не вдалося завантажити сторінку за цим посиланням. Перевірте URL.")
        return

    subscription_id = await db.add_subscription(message.chat.id, label, url)
    if subscription_id is None:
        await message.answer("Така підписка вже існує.")
        return

    # Позначаємо поточні оголошення як переглянуті, щоб не засипати
    # повідомленнями про все, що вже висить на сайті.
    await db.mark_ads_seen(subscription_id, [ad.ad_id for ad in ads])
    await message.answer(
        f"Підписку «{label}» додано (id {subscription_id}).\n"
        f"Знайдено {len(ads)} поточних оголошень — про нові повідомлю окремо."
    )


@router.message(Command("list"))
async def cmd_list(message: Message, db: Database) -> None:
    subscriptions = await db.list_subscriptions(message.chat.id)
    if not subscriptions:
        await message.answer("У вас поки немає підписок. Додайте через /add.")
        return

    lines = [f"#{row['id']} — {row['label']}\n{row['url']}" for row in subscriptions]
    await message.answer("\n\n".join(lines))


@router.message(Command("remove"))
async def cmd_remove(message: Message, db: Database) -> None:
    args = (message.text or "").split(maxsplit=1)[1:]
    if not args or not args[0].isdigit():
        await message.answer("Формат: /remove id. Побачити id можна через /list.")
        return

    removed = await db.remove_subscription(message.chat.id, int(args[0]))
    await message.answer("Підписку видалено." if removed else "Підписку не знайдено.")


@router.message(Command("preview"))
async def cmd_preview(message: Message, db: Database, config: Config) -> None:
    args = (message.text or "").split(maxsplit=1)[1:]
    if not args or not args[0].isdigit():
        await message.answer("Формат: /preview id. Побачити id можна через /list.")
        return

    row = await db.get_subscription(message.chat.id, int(args[0]))
    if row is None:
        await message.answer("Підписку не знайдено.")
        return

    try:
        ads = await fetch_ads(row["url"], timeout=config.request_timeout, max_pages=config.max_pages)
    except Exception:
        await message.answer("Не вдалося завантажити сторінку за цим посиланням.")
        return

    if not ads:
        await message.answer("За цим посиланням поки нічого не знайдено.")
        return

    preview_ads = ads[:PREVIEW_COUNT]
    await message.answer(
        f"Показую {len(preview_ads)} з {len(ads)} поточних оголошень "
        f"(без позначення «баченими» — на майбутні сповіщення це не впливає):"
    )
    for ad in preview_ads:
        try:
            await send_ad(message.bot, message.chat.id, row["label"], ad, config)
            await asyncio.sleep(0.5)
        except Exception as exc:
            logger.warning("Не вдалося надіслати прев'ю %s: %s", message.chat.id, exc)


@router.message(Command("check"))
async def cmd_check(message: Message, db: Database, config: Config) -> None:
    subscriptions = await db.list_subscriptions(message.chat.id)
    if not subscriptions:
        await message.answer("У вас немає підписок для перевірки.")
        return

    await message.answer("Перевіряю...")
    for row in subscriptions:
        try:
            ads = await fetch_ads(row["url"], timeout=config.request_timeout, max_pages=config.max_pages)
        except Exception:
            continue

        seen = await db.get_seen_ad_ids(row["id"])
        new_ads = [ad for ad in ads if ad.ad_id not in seen][: config.max_ads_per_check]
        await db.mark_ads_seen(row["id"], [ad.ad_id for ad in ads])

        for ad in new_ads:
            try:
                await send_ad(message.bot, message.chat.id, row["label"], ad, config)
                await asyncio.sleep(0.5)
            except Exception as exc:
                logger.warning("Не вдалося надіслати повідомлення %s: %s", message.chat.id, exc)

    await message.answer("Перевірку завершено.")
