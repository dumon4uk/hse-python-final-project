from project.services.formats import build_audio_menu, build_video_menu


def test_build_audio_menu_picks_best(fake_info):
    fake_info["formats"] = [
        {"format_id": "v1", "vcodec": "h264", "acodec": "none", "ext": "mp4", "height": 720},
        {"format_id": "a_low", "vcodec": "none", "acodec": "aac", "ext": "m4a", "abr": 96, "filesize": 10_000_000},
        {"format_id": "a_hi", "vcodec": "none", "acodec": "aac", "ext": "m4a", "abr": 160, "filesize": 15_000_000},
    ]

    menu = build_audio_menu(fake_info, limit=10)

    assert len(menu) == 2
    assert menu[0]["id"] == "a_hi"
    assert "🎧" in menu[0]["label"]


def test_build_video_menu_merges_best_audio_when_video_has_no_audio(fake_info):
    fake_info["formats"] = [
        {"format_id": "a1", "vcodec": "none", "acodec": "aac", "ext": "m4a", "abr": 160, "filesize": 5_000_000},
        {"format_id": "a2", "vcodec": "none", "acodec": "aac", "ext": "m4a", "abr": 96, "filesize": 3_000_000},
        {"format_id": "v720", "vcodec": "h264", "acodec": "none", "ext": "mp4", "height": 720, "filesize": 20_000_000},
        {"format_id": "v480", "vcodec": "h264", "acodec": "none", "ext": "mp4", "height": 480, "filesize": 12_000_000},
    ]

    menu = build_video_menu(fake_info, limit=10)

    assert menu[0]["height"] == 720
    assert menu[0]["id"] == "v720+a1"
    assert "+audio" in menu[0]["label"]
