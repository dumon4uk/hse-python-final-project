from __future__ import annotations

import asyncio
import re
import time
from typing import Any
from collections import defaultdict

from aiogram import F
from aiogram import Router
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from project.downloader.ytdlp_client import extract_info
from project.services.formats import build_audio_menu, build_video_menu
from project.services.download import (
    DownloadRequest,
    make_job_dir,
    cleanup_dir,
    download_and_prepare_sync,
)
from project.services.uploader import send_file_smart
from project.states.download import DownloadStates
from project.utils.config import settings

router = Router()

URL_RE = re.compile(r"https?://\S+")

# Prevent parallel downloads per chat
_chat_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


def kb_type() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎬 Видео", callback_data="dl:type:video")],
            [
                InlineKeyboardButton(text="🎧 Аудио (mp3)", callback_data="dl:type:audio_mp3"),
                InlineKeyboardButton(text="🎧 Аудио (ориг.)", callback_data="dl:type:audio_orig"),
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


def _fmt_duration(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}ч {m}м {s}с"
    if m:
        return f"{m}м {s}с"
    return f"{s}с"


@router.message(F.text & ~F.text.startswith("/"))
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


@router.callback_query(lambda c: c.data.startswith("dl:type:"))
async def on_type_selected(call: CallbackQuery, state: FSMContext) -> None:
    choice = call.data.split("dl:type:", 1)[1]  # video | audio_mp3 | audio_orig
    data = await state.get_data()
    url = data.get("url")
    if not url:
        await state.clear()
        await call.message.edit_text("Не вижу ссылку. Пришли ссылку заново.")
        await call.answer()
        return

    await call.answer("Получаю список форматов…")

    info = await asyncio.to_thread(extract_info, url, settings.COOKIES_FILE)

    # Duration guard
    dur = info.get("duration")
    if isinstance(dur, (int, float)) and dur > settings.MAX_DURATION_SECONDS:
        await state.clear()
        await call.message.edit_text(
            "⛔️ Слишком длинное видео.\n"
            f"Длительность: {_fmt_duration(int(dur))}\n"
            f"Лимит: {_fmt_duration(int(settings.MAX_DURATION_SECONDS))}\n\n"
            "Пришли другую ссылку."
        )
        return

    if choice == "video":
        menu = build_video_menu(info)
        title = "Выбери качество видео:"
        await state.update_data(media="video", audio_mode=None)
    elif choice == "audio_mp3":
        menu = build_audio_menu(info)
        title = "Выбери качество аудио (конвертация в mp3):"
        await state.update_data(media="audio", audio_mode="mp3")
    else:
        menu = build_audio_menu(info)
        title = "Выбери качество аудио (оригинальный формат):"
        await state.update_data(media="audio", audio_mode="orig")

    if not menu:
        await state.clear()
        await call.message.edit_text("Не нашёл подходящих форматов. Попробуй другую ссылку.")
        return

    await state.set_state(DownloadStates.waiting_format)
    await call.message.edit_text(title, reply_markup=kb_formats(menu))


@router.callback_query(lambda c: c.data.startswith("dl:fmt:"))
async def on_format_selected(call: CallbackQuery, state: FSMContext) -> None:
    import os
    import logging

    log = logging.getLogger(__name__)
    chat_id = call.message.chat.id

    format_id = call.data.split("dl:fmt:", 1)[1]

    data = await state.get_data()
    url = data.get("url")
    media = data.get("media")            # "video" | "audio"
    audio_mode = data.get("audio_mode")  # "mp3" | "orig" | None

    if not url:
        await state.clear()
        await call.message.edit_text("Не вижу ссылку. Пришли ссылку заново.")
        await call.answer()
        return

    lock = _chat_locks[chat_id]
    if lock.locked():
        await call.answer("⏳ Уже качаю. Подожди завершения 🙂", show_alert=True)
        return

    async with lock:
        await state.set_state(DownloadStates.downloading)

        progress_msg = await call.message.edit_text("⬇️ Начинаю загрузку…")
        await call.answer()

        loop = asyncio.get_running_loop()
        last_edit = {"t": 0.0}
        last_text = {"v": ""}

        def hook(d: dict[str, Any]) -> None:
            # This hook is called from a worker thread (yt-dlp)
            status = d.get("status")

            now = time.monotonic()
            if now - last_edit["t"] < 1.2:
                return
            last_edit["t"] = now

            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                if total:
                    pct = int(downloaded * 100 / total)
                    text = f"⬇️ Скачиваю… {pct}%"
                else:
                    text = "⬇️ Скачиваю…"
            elif status == "finished":
                text = "✅ Скачано. Обрабатываю…"
            else:
                return

            if text == last_text["v"]:
                return
            last_text["v"] = text

            # Thread-safe scheduling into the main event loop
            try:
                asyncio.run_coroutine_threadsafe(progress_msg.edit_text(text), loop)
            except Exception:
                pass

        job_dir = make_job_dir(settings.DOWNLOADS_DIR, chat_id=chat_id)

        file_path: str | None = None
        try:
            to_mp3 = (media == "audio" and audio_mode == "mp3")

            req = DownloadRequest(
                url=url,
                format_id=format_id,
                to_mp3=to_mp3,
            )

            file_path = await asyncio.to_thread(
                download_and_prepare_sync,
                req,
                job_dir,
                hook,
            )

            if (not file_path) or (not os.path.exists(file_path)) or os.path.getsize(file_path) == 0 or file_path.endswith(".part"):
                await state.clear()
                await progress_msg.edit_text(
                    "❌ Скачался пустой файл.\n"
                    "Часто это ограничения сайта (403/429/гео/нужны cookies) или проблемы с фрагментами.\n"
                    "Попробуй другую ссылку или позже."
                )
                return

        except Exception:
            log.exception("Download failed: url=%s format=%s", url, format_id)
            await state.clear()
            await progress_msg.edit_text(
                "❌ Ошибка скачивания.\n"
                "Если выбирал mp3 — проверь, что установлен ffmpeg.\n"
                "Если сайт капризный — попробуй cookies (COOKIES_FILE)."
            )
            return

        # sending file (smart)
        try:
            await progress_msg.edit_text("📤 Отправляю файл…")
            await send_file_smart(call.bot, chat_id, file_path)
            await progress_msg.edit_text("✅ Готово! Пришли ещё ссылку 🙂")

        except Exception as e:
            log.exception("Send failed: file=%s err=%s", file_path, e)
            await progress_msg.edit_text(
                "❌ Не смог отправить файл.\n"
                "Если файл большой — настрой Telethon (TELETHON_API_ID/TELETHON_API_HASH).\n"
                "Или выбери меньшее качество."
            )

        finally:
            cleanup_dir(job_dir)
            await state.clear()
