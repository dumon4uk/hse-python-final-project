from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from project.downloader.ytdlp_client import download as ytdlp_download, ProgressHook
from project.utils.config import settings


@dataclass
class DownloadRequest:
    url: str
    format_id: str
    to_mp3: bool = False


def make_job_dir(base_dir: str, chat_id: int | None = None) -> str:
    job = uuid.uuid4().hex[:12]
    if chat_id is None:
        return str(Path(base_dir) / job)
    return str(Path(base_dir) / str(chat_id) / job)


def cleanup_dir(path: str) -> None:
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


def download_and_prepare_sync(
    req: DownloadRequest,
    out_dir: str,
    progress_hook: Optional[ProgressHook] = None,
) -> str:
    return ytdlp_download(
        req.url,
        req.format_id,
        out_dir,
        progress_hook=progress_hook,
        to_mp3=req.to_mp3,
        cookies_file=settings.COOKIES_FILE,
    )
