from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "📥 Пришли ссылку на видео или аудио\n\n"
        "🎬 Видео — выбор качества\n"
        "🎧 Аудио (mp3) — универсальный формат\n"
        "🎧 Аудио (ориг.) — без перекодирования\n\n"
        "⚠️ Если видео недоступно — могут понадобиться cookies\n"
        "📦 Большие файлы отправляются через Telethon"
    )
