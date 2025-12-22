from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    BOT_TOKEN: str
    DOWNLOADS_DIR: str = "data/downloads"

    # safety/limits
    MAX_DURATION_SECONDS: int = 60 * 60  # 1 hour by default

    # Optional: cookies.txt path for sites that require auth/age/geo
    COOKIES_FILE: str | None = None

    # Telethon (optional, for sending big files)
    TELETHON_API_ID: int | None = None
    TELETHON_API_HASH: str | None = None
    TELETHON_SESSION: str = "data/telethon_bot"


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def _opt_env(name: str) -> str | None:
    v = os.getenv(name)
    return v if v else None


def _opt_int(name: str) -> int | None:
    v = _opt_env(name)
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        raise RuntimeError(f"Environment variable {name} must be int")


settings = Settings(
    BOT_TOKEN=_opt_env("BOT_TOKEN"),
    DOWNLOADS_DIR=os.getenv("DOWNLOADS_DIR", "data/downloads"),
    MAX_DURATION_SECONDS=int(os.getenv("MAX_DURATION_SECONDS", str(60 * 60))),
    COOKIES_FILE=_opt_env("COOKIES_FILE"),
    TELETHON_API_ID=_opt_int("TELETHON_API_ID"),
    TELETHON_API_HASH=_opt_env("TELETHON_API_HASH"),
    TELETHON_SESSION=os.getenv("TELETHON_SESSION", "data/telethon_bot"),
)
