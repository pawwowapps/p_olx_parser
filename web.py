from aiohttp import web

from bot.config import load_config
from bot.webhook_app import create_app

if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=load_config().port)
