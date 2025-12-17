from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    BOT_TOKEN: str
    DOWNLOADS_DIR: str = "data/downloads"


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


settings = Settings(
    BOT_TOKEN=_require_env("BOT_TOKEN"),
)
