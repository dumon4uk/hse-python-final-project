from __future__ import annotations

import asyncio
import re
import time
from typing import Any

from aiogram import Router
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.types.input_file import FSInputFile

from project.downloader.ytdlp_client import extract_info, download as ytdlp_download
from project.services.formats import build_audio_menu, build_video_menu
from project.states.download import DownloadStates
from project.utils.config import settings

router = Router()

URL_RE = re.compile(r"https?://\S+")


def kb_type() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎬 Видео", callback_data="dl:type:video"),
                InlineKeyboardButton(text="🎧 Аудио", callback_data="dl:type:audio"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="dl:cancel")],
        ]
    )


def kb_formats(menu: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    rows = []
    for item in menu:
        rows.append([InlineKeyboardButton(text=item["label"], callback_data=f"dl:fmt:{item['id']}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="dl:back:type")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="dl:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message()
async def on_any_message(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    m = URL_RE.search(text)
    if not m:
        return

    url = m.group(0)

    await state.clear()
    await state.update_data(url=url)
    await state.set_state(DownloadStates.waiting_type)

    await message.answer(
        f"✅ Ссылка получена:\n<code>{url}</code>\n\nЧто скачать?",
        reply_markup=kb_type(),
    )


@router.callback_query(lambda c: c.data == "dl:cancel")
async def on_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text("Ок, отменено. Пришли новую ссылку.")
    await call.answer()


@router.callback_query(lambda c: c.data == "dl:back:type")
async def on_back_to_type(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    url = data.get("url")
    await state.set_state(DownloadStates.waiting_type)
    await call.message.edit_text(
        f"✅ Ссылка:\n<code>{url}</code>\n\nЧто скачать?",
        reply_markup=kb_type(),
    )
    await call.answer()


@router.callback_query(lambda c: c.data in ("dl:type:video", "dl:type:audio"))
async def on_type_selected(call: CallbackQuery, state: FSMContext) -> None:
    choice = call.data.split(":")[-1]
    data = await state.get_data()
    url = data.get("url")
    if not url:
        await state.clear()
        await call.message.edit_text("Не вижу ссылку. Пришли ссылку заново.")
        await call.answer()
        return

    await call.answer("Получаю список форматов…")

    # extract_info is heavy
    info = await asyncio.to_thread(extract_info, url)

    if choice == "video":
        menu = build_video_menu(info)
        title = "Выбери качество видео:"
    else:
        menu = build_audio_menu(info)
        title = "Выбери качество аудио:"

    if not menu:
        await state.clear()
        await call.message.edit_text("Не нашёл подходящих форматов. Попробуй другую ссылку.")
        return

    await state.update_data(choice=choice)
    await state.set_state(DownloadStates.waiting_format)

    await call.message.edit_text(title, reply_markup=kb_formats(menu))


@router.callback_query(lambda c: c.data.startswith("dl:fmt:"))
async def on_format_selected(call: CallbackQuery, state: FSMContext) -> None:
    import os
    import logging

    log = logging.getLogger(__name__)

    format_id = call.data.split("dl:fmt:", 1)[1]

    data = await state.get_data()
    url = data.get("url")
    if not url:
        await state.clear()
        await call.message.edit_text("Не вижу ссылку. Пришли ссылку заново.")
        await call.answer()
        return

    await state.set_state(DownloadStates.downloading)

    progress_msg = await call.message.edit_text("⬇️ Начинаю загрузку…")
    await call.answer()

    loop = asyncio.get_running_loop()
    last_edit = {"t": 0.0}

    def hook(d: dict[str, Any]) -> None:
        status = d.get("status")
        if status != "downloading":
            return

        now = time.monotonic()
        if now - last_edit["t"] < 1.2:
            return
        last_edit["t"] = now

        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        downloaded = d.get("downloaded_bytes") or 0
        if total:
            pct = int(downloaded * 100 / total)
            text = f"⬇️ Скачиваю… {pct}%"
        else:
            text = "⬇️ Скачиваю…"

        async def _edit() -> None:
            try:
                await progress_msg.edit_text(text)
            except Exception:
                pass

        loop.call_soon_threadsafe(lambda: asyncio.create_task(_edit()))

    file_path: str | None = None
    try:
        file_path = await asyncio.to_thread(
            ytdlp_download,
            url,
            format_id,
            settings.DOWNLOADS_DIR,
            hook,
        )

        # empty files
        if (not file_path) or (not os.path.exists(file_path)) or os.path.getsize(file_path) == 0 or file_path.endswith(".part"):
            # cleaning garbage
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass

            await state.clear()
            await progress_msg.edit_text(
                "❌ Скачался пустой файл.\n"
                "Обычно это ограничения сайта (403/429/гео/нужны cookies) или проблемы с фрагментами.\n"
                "Попробуй другую ссылку или позже."
            )
            return

    except Exception as e:
        log.exception("Download failed: url=%s format=%s", url, format_id)
        await state.clear()
        await progress_msg.edit_text("❌ Ошибка скачивания. Попробуй другую ссылку или позже.")
        return

    # sending file
    try:
        await progress_msg.edit_text("📤 Отправляю файл…")
        await call.message.answer_document(FSInputFile(file_path))
        await progress_msg.edit_text("✅ Готово! Пришли ещё ссылку 🙂")

    except Exception:
        log.exception("Send failed: file=%s", file_path)
        await progress_msg.edit_text("❌ Не смог отправить файл в Telegram (возможно, слишком большой).")
    finally:
        # cleaning after sending/fail
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        await state.clear()

