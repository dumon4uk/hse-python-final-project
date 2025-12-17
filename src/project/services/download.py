from dataclasses import dataclass
from typing import Optional


@dataclass
class DownloadRequest:
    url: str
    format_id: str
    is_audio: bool = False
    target_ext: Optional[str] = None


async def download_and_prepare(req: DownloadRequest) -> str:
    raise NotImplementedError
