from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional, Callable

from aiogram import Bot
from aiogram.types.input_file import FSInputFile

from project.utils.config import settings

log = logging.getLogger(__name__)

_telethon_client = None


async def _get_telethon_client():
    global _telethon_client
    if _telethon_client is not None:
        return _telethon_client

    if not settings.TELETHON_API_ID or not settings.TELETHON_API_HASH:
        return None

    from telethon import TelegramClient

    client = TelegramClient(
        settings.TELETHON_SESSION,
        settings.TELETHON_API_ID,
        settings.TELETHON_API_HASH,
    )

    await client.connect()

    if not await client.is_user_authorized():
        await client.sign_in(bot_token=settings.BOT_TOKEN)

    _telethon_client = client
    return _telethon_client



async def close_telethon_client() -> None:
    global _telethon_client
    if _telethon_client is None:
        return
    try:
        await _telethon_client.disconnect()
    except Exception:
        pass
    _telethon_client = None


def _looks_like_too_big_error(e: Exception) -> bool:
    s = str(e).lower()
    return (
        "request entity too large" in s
        or "entity too large" in s
        or "file is too big" in s
        or "file too big" in s
        or "too large" in s
    )


async def send_file_smart(
    bot: Bot,
    chat_id: int,
    file_path: str | Path,
    caption: Optional[str] = None,
    on_progress: Optional[Callable[[int], None]] = None,  # percent
) -> None:
    path = Path(file_path)

    # 1) Try Bot API
    try:
        await bot.send_document(
            chat_id=chat_id,
            document=FSInputFile(str(path)),
            caption=caption,
        )
        if on_progress:
            on_progress(100)
        return
    except Exception as e:
        log.warning("Bot API send failed: %s", e)

        client = await _get_telethon_client()
        if client is None:
            raise

        # 2) Telethon fallback (with upload progress)
        last_emit = 0.0
        last_pct = -1

        def progress_callback(sent: int, total: int) -> None:
            nonlocal last_emit, last_pct
            if total <= 0:
                return
            pct = int(sent * 100 / total)
            now = time.monotonic()
            # throttle updates
            if pct == last_pct:
                return
            if now - last_emit < 1.0 and pct < 100:
                return
            last_emit = now
            last_pct = pct
            if on_progress:
                on_progress(pct)

        try:
            await client.send_file(
                entity=chat_id,
                file=str(path),
                caption=caption or "",
                progress_callback=progress_callback,
            )
            if on_progress:
                on_progress(100)
            return
        except Exception as e2:
            log.exception("Telethon send failed: %s", e2)
            if _looks_like_too_big_error(e) or _looks_like_too_big_error(e2):
                raise RuntimeError("FILE_TOO_BIG")
            raise
