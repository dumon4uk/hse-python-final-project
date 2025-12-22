import asyncio
import os

from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from project.handlers import router as main_router
from project.utils.config import settings
from project.utils.logging import setup_logging
from project.services.uploader import close_telethon_client


def create_bot() -> Bot:
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def ensure_dirs() -> None:
    os.makedirs(settings.DOWNLOADS_DIR, exist_ok=True)
    os.makedirs("data", exist_ok=True)


async def on_shutdown(_: Bot) -> None:
    await close_telethon_client()


async def main() -> None:
    setup_logging()
    ensure_dirs()

    bot = create_bot()
    dp = Dispatcher()
    dp.include_router(main_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, on_shutdown=on_shutdown)


if __name__ == "__main__":
    asyncio.run(main())
