from pathlib import Path
from project.downloader.ytdlp_client import _pick_best_existing_file


def test_pick_best_existing_file(tmp_path):
    video_id = "abc"

    p1 = tmp_path / f"t1 [{video_id}].mp4"
    p2 = tmp_path / f"t2 [{video_id}].mp4"
    p1.write_bytes(b"x" * 10)
    p2.write_bytes(b"x" * 100)

    best = _pick_best_existing_file(str(tmp_path), video_id)

    assert Path(best).name == p2.name


def test_pick_best_ignores_part_files(tmp_path):
    video_id = "abc"

    part = tmp_path / f"t1 [{video_id}].mp4.part"
    good = tmp_path / f"t2 [{video_id}].mp4"
    part.write_bytes(b"x" * 999)
    good.write_bytes(b"x" * 5)

    best = _pick_best_existing_file(str(tmp_path), video_id)

    assert Path(best).name == good.name
