from __future__ import annotations

from typing import Any


def _filesize(fmt: dict[str, Any]) -> int:
    return int(fmt.get("filesize") or fmt.get("filesize_approx") or 0)


def _mb(n: int) -> str:
    if n <= 0:
        return "?"
    return f"{max(1, n // 1_000_000)} MB"


def build_audio_menu(info: dict[str, Any], limit: int = 6) -> list[dict[str, Any]]:
    formats = info.get("formats") or []
    audio = []
    for f in formats:
        if f.get("vcodec") != "none":
            continue
        if f.get("acodec") in (None, "none"):
            continue
        abr = f.get("abr") or 0
        size = _filesize(f)
        audio.append(
            {
                "id": f.get("format_id"),
                "label": f"🎧 {f.get('ext','audio')} {int(abr) if abr else '?'} kbps (~{_mb(size)})",
                "abr": abr,
                "ext": f.get("ext"),
                "filesize": size,
                "type": "audio",
            }
        )

    audio.sort(key=lambda x: (x.get("abr") or 0, x.get("filesize") or 0), reverse=True)
    return [a for a in audio if a.get("id")][:limit]


def build_video_menu(info: dict[str, Any], limit: int = 6) -> list[dict[str, Any]]:
    formats = info.get("formats") or []

    # choosing best audio
    best_audio = None
    for f in formats:
        if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none"):
            if best_audio is None or (f.get("abr") or 0) > (best_audio.get("abr") or 0):
                best_audio = f

    # video
    videos = []
    for f in formats:
        if f.get("vcodec") in (None, "none"):
            continue
        h = f.get("height")
        if not h:
            continue
        ext = f.get("ext")
        size = _filesize(f)
        has_audio = f.get("acodec") not in (None, "none")
        videos.append(
            {
                "format_id": f.get("format_id"),
                "height": int(h),
                "ext": ext,
                "filesize": size,
                "has_audio": has_audio,
            }
        )

    # choosing best video for each height
    by_height: dict[int, dict[str, Any]] = {}
    for v in videos:
        h = v["height"]
        cur = by_height.get(h)
        if cur is None:
            by_height[h] = v
            continue

        score_cur = (1 if cur["has_audio"] else 0, cur["filesize"])
        score_new = (1 if v["has_audio"] else 0, v["filesize"])
        if score_new > score_cur:
            by_height[h] = v

    heights = sorted(by_height.keys(), reverse=True)
    menu: list[dict[str, Any]] = []

    for h in heights:
        v = by_height[h]
        vid = v["format_id"]
        if not vid:
            continue

        if v["has_audio"]:
            fmt_id = str(vid)
            suffix = ""
        else:
            if best_audio and best_audio.get("format_id"):
                # merging
                fmt_id = f"{vid}+{best_audio['format_id']}"
                suffix = " +audio"
            else:
                # only video
                fmt_id = str(vid)
                suffix = ""

        menu.append(
            {
                "id": fmt_id,
                "label": f"🎬 {h}p {v.get('ext','video')}{suffix} (~{_mb(v.get('filesize', 0))})",
                "height": h,
                "ext": v.get("ext"),
                "filesize": v.get("filesize", 0),
                "type": "video",
            }
        )

        if len(menu) >= limit:
            break

    return menu
