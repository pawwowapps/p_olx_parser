from __future__ import annotations

from aiogram import Bot
from aiogram.types import BotCommand

COMMANDS = [
    BotCommand(command="add", description="Додати пошук OLX для відстеження"),
    BotCommand(command="list", description="Показати активні підписки"),
    BotCommand(command="preview", description="Показати кілька поточних оголошень підписки"),
    BotCommand(command="check", description="Перевірити всі підписки прямо зараз"),
    BotCommand(command="remove", description="Видалити підписку"),
    BotCommand(command="help", description="Довідка про команди"),
]


async def set_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(COMMANDS)
