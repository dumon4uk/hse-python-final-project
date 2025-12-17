from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

router = Router()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Привет! 👋\n"
        "Пришли ссылку на видео/аудио (YouTube/Vimeo/TikTok и т.д.)."
    )
