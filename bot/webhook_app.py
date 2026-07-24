from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import Config, load_config
from .db.database import Database
from .handlers import start, subscriptions
from .scheduler import check_subscriptions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

WEBHOOK_PATH = "/webhook"


def create_app() -> web.Application:
    config = load_config()
    if not config.webhook_url:
        raise RuntimeError(
            "WEBHOOK_URL не задано (і RENDER_EXTERNAL_URL відсутній). "
            "Для локального запуску використовуйте run.py (polling)."
        )
    if not config.webhook_secret:
        raise RuntimeError("WEBHOOK_SECRET не задано. Згенеруйте випадковий рядок і додайте у змінні середовища.")

    bot = Bot(token=config.bot_token)
    db = Database(config.db_path)
    scheduler = AsyncIOScheduler()

    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(subscriptions.router)

    @dp.startup()
    async def on_startup(bot: Bot, db: Database, config: Config) -> None:
        await db.init()
        await bot.set_webhook(
            url=f"{config.webhook_url}{WEBHOOK_PATH}",
            secret_token=config.webhook_secret,
            drop_pending_updates=True,
        )
        scheduler.add_job(
            check_subscriptions,
            trigger="interval",
            minutes=config.check_interval_minutes,
            args=(bot, db, config),
        )
        scheduler.start()

    @dp.shutdown()
    async def on_shutdown(bot: Bot) -> None:
        # НЕ викликаємо bot.delete_webhook() тут: на безкоштовному Render
        # інстанс засинає через бездіяльність і коректно завершує процес
        # (звідси й цей shutdown-хук), а видалений вебхук означає, що
        # Telegram більше нікуди не надсилає оновлення — і немає вхідного
        # запиту, який міг би розбудити інстанс назад. Вебхук лишається
        # зареєстрованим між рестартами, а on_startup при наступному
        # старті просто перереєструє той самий URL.
        scheduler.shutdown(wait=False)
        await bot.session.close()

    app = web.Application()

    async def health(request: web.Request) -> web.Response:
        return web.Response(text="ok")

    app.router.add_get("/", health)

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=config.webhook_secret,
        db=db,
        config=config,
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot, db=db, config=config)

    return app
