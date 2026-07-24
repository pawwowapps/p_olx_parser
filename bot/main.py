from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .commands import set_bot_commands
from .config import load_config
from .db.database import Database
from .handlers import start, subscriptions
from .scheduler import check_subscriptions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def main() -> None:
    config = load_config()

    db = Database(config.db_path)
    await db.init()

    bot = Bot(token=config.bot_token)
    await set_bot_commands(bot)

    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(subscriptions.router)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_subscriptions,
        trigger="interval",
        minutes=config.check_interval_minutes,
        args=(bot, db, config),
    )
    scheduler.start()

    try:
        await dp.start_polling(bot, db=db, config=config)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
