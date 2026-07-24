from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="start")

HELP_TEXT = (
    "Я стежу за новими оголошеннями на OLX і надсилаю їх сюди з фото, ціною, "
    "описом і посиланням.\n\n"
    "Критерії (категорія, ціна, кімнати, район тощо) задаються не тут, а на "
    "самому olx.ua: зайдіть на сайт, виставте потрібні фільтри пошуку і "
    "скопіюйте посилання, що вийшло — я парситиму саме те, що показує ця "
    "сторінка.\n\n"
    "Команди:\n"
    "/add назва посилання — додати пошук OLX для відстеження\n"
    "/list — показати активні підписки\n"
    "/remove id — видалити підписку\n"
    "/check — перевірити всі підписки прямо зараз\n"
    "/help — показати це повідомлення\n\n"
    "Приклад (оренда квартир у Києві):\n"
    "/add кв_київ https://www.olx.ua/uk/nedvizhimost/kvartiry/dolgosrochnaya-arenda-kvartir/kiev/"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(f"Привіт!\n\n{HELP_TEXT}")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
