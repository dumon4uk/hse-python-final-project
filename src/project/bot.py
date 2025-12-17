import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from project.handlers import router as main_router
from project.utils.config import settings
from project.utils.logging import setup_logging


def create_bot() -> Bot:
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def ensure_dirs() -> None:
    os.makedirs(settings.DOWNLOADS_DIR, exist_ok=True)


async def main() -> None:
    setup_logging()
    ensure_dirs()

    bot = create_bot()
    dp = Dispatcher()
    dp.include_router(main_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
