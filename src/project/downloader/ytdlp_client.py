from __future__ import annotations

from typing import Any, Callable, Dict, Optional
import os
import glob
import logging
import yt_dlp


log = logging.getLogger(__name__)

ProgressHook = Callable[[Dict[str, Any]], None]


def extract_info(url: str, cookies_file: str | None = None) -> Dict[str, Any]:
    ydl_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def _pick_best_existing_file(out_dir: str, video_id: str) -> Optional[str]:
    if not video_id:
        return None

    patterns = [
        os.path.join(out_dir, f"*[{video_id}].*"),
        os.path.join(out_dir, f"*{video_id}*"),
    ]
    candidates: list[str] = []
    for p in patterns:
        candidates.extend(glob.glob(p))

    candidates = [
        c for c in candidates
        if os.path.isfile(c) and not c.endswith(".part") and os.path.getsize(c) > 0
    ]
    if not candidates:
        return None

    return max(candidates, key=lambda x: os.path.getsize(x))


def download(
    url: str,
    format_id: str,
    out_dir: str,
    progress_hook: Optional[ProgressHook] = None,
    to_mp3: bool = False,
    cookies_file: str | None = None,
) -> str:
    """
    Downloads media using yt-dlp and returns a path to the final file.

    If to_mp3=True, yt-dlp will extract audio and convert it to mp3 using ffmpeg.
    (ffmpeg must be installed on the machine).

    cookies_file: path to cookies.txt (optional).
    """
    os.makedirs(out_dir, exist_ok=True)

    hooks = []
    if progress_hook:
        hooks.append(progress_hook)

    ydl_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": format_id,
        "outtmpl": os.path.join(out_dir, "%(title).200s [%(id)s].%(ext)s"),
        "progress_hooks": hooks,
        "merge_output_format": "mp4",
        "retries": 10,
        "fragment_retries": 10,
        "file_access_retries": 5,
        "extractor_retries": 5,
        "socket_timeout": 20,
    }

    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file

    if to_mp3:
        # Convert extracted audio to mp3 via ffmpeg
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

        # Sometimes yt-dlp provides direct filepath
        fp = info.get("filepath")
        if fp and os.path.exists(fp) and os.path.getsize(fp) > 0 and not fp.endswith(".part"):
            return fp

        # Sometimes filepaths are inside requested_downloads
        req = info.get("requested_downloads")
        if isinstance(req, list) and req:
            for item in reversed(req):
                fp2 = item.get("filepath")
                if fp2 and os.path.exists(fp2) and os.path.getsize(fp2) > 0 and not fp2.endswith(".part"):
                    return fp2

        # Try prepared filename
        try:
            p = ydl.prepare_filename(info)
            if p and os.path.exists(p) and os.path.getsize(p) > 0 and not p.endswith(".part"):
                return p
        except Exception:
            pass

        best = _pick_best_existing_file(out_dir, info.get("id", ""))
        if best:
            return best

        raise RuntimeError("The downloaded file is empty or missing")
