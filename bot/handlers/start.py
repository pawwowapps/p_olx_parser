from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="start")

HELP_TEXT = (
    "Я стежу за новими оголошеннями на OLX і надсилаю їх сюди.\n\n"
    "Команди:\n"
    "/add назва посилання — додати пошук OLX для відстеження\n"
    "/list — показати активні підписки\n"
    "/remove id — видалити підписку\n"
    "/check — перевірити всі підписки прямо зараз\n"
    "/help — показати це повідомлення\n\n"
    "Приклад:\n"
    "/add iphone https://www.olx.ua/uk/list/q-iphone-15/"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(f"Привіт!\n\n{HELP_TEXT}")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
